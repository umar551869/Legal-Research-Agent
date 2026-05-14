import logging
import asyncio
import json
import re
import time
from datetime import datetime
from typing import Optional, AsyncGenerator, List, Dict, Any
from app.core.assistant_context import SYSTEM_CAPABILITY_CONTEXT
from app.core.ollama_utils import OllamaClient
from app.core.web_search import create_web_search_tool
from app.core.embedding_store import initialize_embedding_model
from app.services.global_kb import global_kb
from app.services.cache import research_cache
from app.config import settings
from supabase import create_client, ClientOptions
from app.core.summarizer import load_summarization_model, generate_summary_with_guardrails

logger = logging.getLogger(__name__)

class ResearchService:
    def __init__(self):
        # 1. Initialize Ollama Client (Lightweight)
        self.ollama = OllamaClient(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            fallback_model=settings.OLLAMA_FALLBACK_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_model=settings.OPENAI_MODEL
        )
        
        # 2. Tools (Lazy loaded later if needed)
        self.web_search_provider = create_web_search_tool()
        
        # 3. Model state - ALL LAZY LOADED
        self.embedding_model = None
        self.sum_tokenizer = None
        self.sum_model = None
        self.sum_device = None
        
        # 4. Stateless History Fallback (RAM based)
        self.stateless_conversations = {} # id -> {title, updated_at, messages: []}
        
        self._embed_lock = asyncio.Lock()
        self._sum_lock = asyncio.Lock()
            
        logger.info("ResearchService initialized (Models will be lazy-loaded on demand)")

    def _is_capability_query(self, query: str) -> bool:
        normalized = query.strip().lower()
        capability_markers = [
            "what are you capable of",
            "what can you do",
            "what tools do you have",
            "what are your tools",
            "how do you work",
            "what is in your codebase",
            "what can this app do",
            "what features do you have",
            "what are your capabilities",
        ]
        return any(marker in normalized for marker in capability_markers)

    def _get_db_client(self, token: Optional[str]):
        if not token:
            return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        options = ClientOptions(headers={"Authorization": f"Bearer {token}"})
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY, options=options)

    async def _ensure_embedding_model(self):
        """Ensure the embedding model is loaded without blocking the event loop."""
        if self.embedding_model is not None:
            return
        async with self._embed_lock:
            if self.embedding_model is not None:
                return
            logger.info("Initializing BGE Embedding model (Lazy Load)...")
            try:
                self.embedding_model = await asyncio.to_thread(initialize_embedding_model)
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")

    async def _ensure_summarizer_loaded(self):
        """Lazy load BART model only when needed."""
        if self.sum_model is not None:
            return
        async with self._sum_lock:
            if self.sum_model is not None:
                return
            logger.info("Initializing BART Summarization model (Lazy Load)...")
            try:
                self.sum_tokenizer, self.sum_model, self.sum_device = await asyncio.to_thread(load_summarization_model)
                logger.info("BART Summarization model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load BART summarization model: {e}")
                self.sum_model = None

    async def _classify_intent(self, query: str) -> str:
        """Enhanced intent classification to favor RESEARCH/SUMMARY for complex queries."""
        clean_query = re.sub(r'[^\w\s]', '', query).strip().lower()
        
        # Heuristic 1: Explicit capability check
        if self._is_capability_query(query):
            return "GENERAL"
            
        # Heuristic 2: Very short or trivial tokens
        conversational_tokens = {"hey", "hello", "hi", "thanks", "ok", "help", "who built you"}
        if clean_query in conversational_tokens or len(clean_query) < 5:
            return "GENERAL"
            
        # Heuristic 3: Legal keywords (force research)
        legal_keywords = {"case", "law", "statute", "court", "ruling", "judgement", "contract", "liability", "punishment", "legal", "article"}
        if any(word in clean_query for word in legal_keywords):
            return "RESEARCH"

        # LLM Classification (Chain-of-Thought style)
        prompt = f"""Task: Classify the user's intent.
Categories:
- 'SUMMARY': Request to summarize a specific legal case or document.
- 'RESEARCH': Legal question, factual inquiry, case law lookup, or complex interpretation.
- 'GENERAL': Greetings, casual chat, meta-questions about the AI, or trivial talk.

User Query: "{query}"

Decision Rule: If the query has ANY legal or factual potential, choose RESEARCH.
Category:"""

        try:
            resp = await self.ollama.generate(prompt, system="Output exactly ONE word: [SUMMARY, RESEARCH, or GENERAL].")
            raw_category = resp.get("response", "RESEARCH").strip().upper()
            if "SUMMARY" in raw_category: return "SUMMARY"
            if "GENERAL" in raw_category: return "GENERAL"
            return "RESEARCH"
        except Exception:
            return "RESEARCH"

    async def _get_optimized_search_query(self, query: str) -> str:
        """Generate a cleaner search query for web engines."""
        prompt = f"""Convert this user request into a targeted search query for a legal professional:
User: "{query}"
Optimized Query:"""
        try:
            resp = await self.ollama.generate(prompt, system="Output ONLY the search query string.")
            return resp.get("response", query).strip().strip('"')
        except:
            return query

    async def get_or_create_conversation(self, user_id: str, conversation_id: Optional[str] = None, title: str = "New Research", token: Optional[str] = None) -> str:
        """Get or create conversation with fail-safe for network errors."""
        if conversation_id: return conversation_id
        
        client = self._get_db_client(token)
        try:
            res = await asyncio.to_thread(lambda: client.table("conversations").insert({"user_id": user_id, "title": title}).execute())
            if res.data:
                return res.data[0]["id"]
            raise Exception("Record insertion failed")
        except Exception as e:
            logger.error(f"Database Error (Conversation): {e}")
            # LOCAL FALLBACK
            conv_id = "stateless-conv-" + str(int(time.time() * 1000))
            self.stateless_conversations[conv_id] = {
                "id": conv_id,
                "user_id": user_id,
                "title": title,
                "updated_at": datetime.utcnow().isoformat(),
                "messages": []
            }
            return conv_id

    async def store_message(self, conversation_id: str, role: str, content: str, token: Optional[str] = None):
        """Save message with fail-safe for network errors."""
        # Clean history in case of "I don't have enough info" legacy responses
        if "Unfortunately, there is not enough information" in content:
            logger.warning("Filtering out generic 'not enough info' response from persistence.")
            return

        if conversation_id in self.stateless_conversations:
            self.stateless_conversations[conversation_id]["messages"].append({
                "role": role,
                "content": content,
                "created_at": datetime.utcnow().isoformat(),
            })
            self.stateless_conversations[conversation_id]["updated_at"] = datetime.utcnow().isoformat()
            return
            
        client = self._get_db_client(token)
        try:
            await asyncio.to_thread(lambda: client.table("messages").insert({"conversation_id": conversation_id, "role": role, "content": content}).execute())
        except Exception as e:
            logger.error(f"Database Error (Message): {e}")
            if conversation_id not in self.stateless_conversations:
                 self.stateless_conversations[conversation_id] = {
                    "id": conversation_id,
                    "title": "Unsaved Conversation",
                    "updated_at": datetime.utcnow().isoformat(),
                    "messages": [{
                        "role": role,
                        "content": content,
                        "created_at": datetime.utcnow().isoformat(),
                    }]
                 }

    async def get_conversation_history(self, conversation_id: str, limit: int = 10, token: Optional[str] = None) -> str:
        """Fetch history with fail-safe for network errors."""
        if conversation_id in self.stateless_conversations:
            history = self.stateless_conversations[conversation_id]["messages"][-limit:]
            return "\n".join([f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}" for m in history]) + "\n"
            
        client = self._get_db_client(token)
        try:
            res = await asyncio.to_thread(lambda: client.table("messages").select("role, content").eq("conversation_id", conversation_id).order("created_at", desc=True).limit(limit).execute())
            history = res.data[::-1]
            if not history: return ""
            return "\n".join([f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}" for m in history]) + "\n"
        except Exception: 
            return ""

    async def list_stateless_conversations(self, user_id: str) -> List[Dict]:
        """Return list of session-local conversations."""
        return [
            {
                "id": c["id"],
                "title": c["title"],
                "updated_at": c["updated_at"],
                "message_count": len(c["messages"])
            }
            for c in self.stateless_conversations.values()
            if c.get("user_id") == user_id or not c.get("user_id")
        ]

    async def run_research_stream(self, query: str, user_id: str, scope: str = "HYBRID", conversation_id: Optional[str] = None, token: Optional[str] = None) -> AsyncGenerator[str, None]:
        conv_id = await self.get_or_create_conversation(user_id, conversation_id, title=query[:50], token=token)
        await self.store_message(conv_id, "user", query, token=token)

        intent = await self._classify_intent(query)
        logger.info(f"Initial Intent: {intent} (Scope: {scope})")

        sources_consulted = []
        retrieved_texts = []
        
        # Yield Sources & Sync Metadata FIRST (Required by Chat Router for first chunk)
        # We yield an empty sources list initially, will be updated in DB later if needed
        # but the first chunk MUST be the metadata JSON.
        yield json.dumps({"sources": [], "conversation_id": conv_id, "intent": intent}) + "\n"

        # Yield status updates as raw tokens (subsequent chunks)
        if intent in ["RESEARCH", "SUMMARY"]:
            yield f"🔍 **Agent Logic:** Classified as {intent}. Starting retrieval pipeline...\n\n"
        else:
            yield "🤖 **Agent Logic:** Conversational query detected. Accessing general knowledge...\n\n"
        
        if intent in ["RESEARCH", "SUMMARY"]:
            retrieval_start = time.time()
            search_query = await self._get_optimized_search_query(query)
            logger.info(f"Using optimized search query: '{search_query}'")

            # 1. External Web Search
            if scope in ["EXTERNAL_WEB", "HYBRID"]:
                try:
                    results = self.web_search_provider.search(search_query, max_results=5)
                    for res in results:
                        retrieved_texts.append(f"[Web Source: {res.title}]({res.url}): {res.snippet}")
                        sources_consulted.append({"title": res.title, "url": res.url, "snippet": res.snippet, "similarity": 0.95, "source_type": "web"})
                except Exception: pass

            # 2. Internal Pinecode DB
            if scope in ["INTERNAL_DB", "HYBRID"]:
                try:
                    internal_results = await global_kb.search(search_query)
                    for res in internal_results:
                        score = res.get("score", 0.0)
                        if score >= 0.75:
                            text = res.get("text", "")
                            meta = res.get("metadata", {})
                            title = meta.get("title", "Internal Case")
                            url = meta.get("url", "#")
                            retrieved_texts.append(f"[Internal Source: {title}]({url}): {text}")
                            sources_consulted.append({"title": title, "url": url, "snippet": text[:200] + "...", "similarity": score, "source_type": "internal"})
                except Exception: pass
            
            # DYNAMIC INTENT SWITCH: If search failed completely, treat as GENERAL knowledge
            if not retrieved_texts:
                logger.info("Search yielded no results. Switching to GENERAL mode for broad knowledge.")
                intent = "GENERAL"
            else:
                # Yield updated sources if we found any
                real_sources = [s for s in sources_consulted if s["url"] != "#" and s["url"].startswith("http")]
                yield json.dumps({"sources": real_sources, "conversation_id": conv_id, "intent": intent}) + "\n"
                yield f"✅ **Search Complete:** Found {len(real_sources)} relevant sources. Synthesizing answer...\n\n"

        history_str = await self.get_conversation_history(conv_id, token=token)
        full_answer = ""

        try:
            if intent == "SUMMARY" and retrieved_texts:
                if self.sum_model is None:
                    yield "Initializing legal summarizer...\n\n"
                    await self._ensure_summarizer_loaded()
                
                if self.sum_model:
                    summary = await asyncio.to_thread(lambda: generate_summary_with_guardrails(query + " " + "\n\n".join(retrieved_texts), retrieved_texts, self.sum_tokenizer, self.sum_model, self.sum_device))
                    full_answer = f"### Legal Case Summary (Grounded by BART)\n\n{summary}"
                    yield full_answer
                else: intent = "GENERAL"

            if intent == "RESEARCH":
                context_str = "\n\n".join(retrieved_texts)
                system_prompt = f"""You are an elite Legal Research Assistant.
**STRICT CITATION RULES:**
1. **Mandatory Links:** For every case, law, or fact you provide from the context, you MUST include a clickable markdown link in the format: [Source Name]({{'URL'}}).
2. **Double Spacing:** Use DOUBLE newlines between paragraphs.
3. **Data Integrity:** Do NOT ignore information in the context.
4. **Capability Honesty:** Only describe tools and system features that exist in the running application.

{SYSTEM_CAPABILITY_CONTEXT}
 
{history_str}"""
                final_prompt = f"User Query: {query}\n\nContext:\n{context_str}"
                async for token in self.ollama.generate_stream(final_prompt, system=system_prompt):
                    full_answer += token
                    yield token

            elif intent == "GENERAL":
                # Mindful Response: If it was originally research but switched, acknowledge it or just answer broadly.
                system_prompt = (
                    "You are a professional Legal Assistant. Provide a helpful response based on your general knowledge. "
                    "If you are citing a case from your own knowledge, mention that you are relying on general information.\n\n"
                    f"{SYSTEM_CAPABILITY_CONTEXT}\n\n{history_str}"
                )
                async for token in self.ollama.generate_stream(query, system=system_prompt):
                    full_answer += token
                    yield token

            await self.store_message(conv_id, "assistant", full_answer, token=token)
        except Exception as e:
            logger.error(f"Stream Error: {e}")
            yield f"\n\n[System Error]: {str(e)}"

    async def run_research(self, query: str, user_id: str, scope: str = "HYBRID", conversation_id: Optional[str] = None, token: Optional[str] = None) -> dict:
        chunks = []
        sources = []
        conv_id = None
        async for chunk in self.run_research_stream(query, user_id, scope, conversation_id, token=token):
            if not conv_id:
                try:
                    meta = json.loads(chunk.strip())
                    sources = meta.get("sources", [])
                    conv_id = meta.get("conversation_id")
                    continue
                except: pass
            chunks.append(chunk)
        return {"answer": "".join(chunks), "sources": sources, "conversation_id": conv_id}

research_service = ResearchService()
