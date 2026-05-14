import logging
import asyncio
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.core.ingestion import chunk_text
from app.core.embedding_store import initialize_embedding_model, embed_texts
from app.config import settings
from pinecone import Pinecone

logger = logging.getLogger(__name__)

class GlobalKnowledgeBase:
    def __init__(self):
        # Model and Index state (Lazy Loaded)
        self.embedding_model = None
        self._embed_lock = asyncio.Lock()
        
        api_key = getattr(settings, "PINECONE_API_KEY", None)
        self.index_name = getattr(settings, "PINECONE_INDEX_NAME", "legal-case-rag-advanced")
        
        if not api_key:
            logger.warning("No Pinecone API key found. Vector search disabled.")
            self.index = None
        else:
            try:
                self.pc = Pinecone(api_key=api_key)
                self.index = self.pc.Index(self.index_name)
                logger.info(f"Connected to Pinecone Index: {self.index_name}")
            except Exception as e:
                logger.error(f"Failed to connect to Pinecone: {e}")
                self.index = None

    async def _ensure_embedding_model(self):
        """Lazy load the embedding model to prevent blocking server startup."""
        if self.embedding_model is not None:
            return
        async with self._embed_lock:
            if self.embedding_model is not None:
                return
            logger.info("Initializing Embedding model for Global KB (Lazy Load)...")
            try:
                self.embedding_model = await asyncio.to_thread(initialize_embedding_model)
                logger.info("Global KB Embedding model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")

    async def ingest_document(self, filename: str, content: str) -> dict:
        """Process and ingest a new document into the knowledge base."""
        if not self.index:
            return {"status": "failed", "reason": "Pinecone not configured"}
            
        try:
            # 1. Ensure model is loaded
            await self._ensure_embedding_model()
            
            # 2. Chunk text
            chunks = chunk_text(content, chunk_size=250, overlap=40)
            if not chunks:
                return {"status": "failed", "reason": "No text content found"}
                
            # 3. Embed chunks
            embeddings = await asyncio.to_thread(
                lambda: embed_texts(chunks, self.embedding_model, show_progress_bar=False)
            )
            
            # 4. Prepare Pinecone vectors
            vectors = []
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                vectors.append({
                    "id": f"{filename}-{i}-{int(time.time())}",
                    "values": emb.tolist(),
                    "metadata": {
                        "text": chunk,
                        "title": filename,
                        "filename": filename,
                        "created_at": datetime.utcnow().isoformat()
                    }
                })
            
            # 5. Batch Upsert to Pinecone
            batch_size = 50
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                await asyncio.to_thread(
                    lambda b=batch: self.index.upsert(vectors=b, namespace=self.index_name)
                )
            
            logger.info(f"Successfully ingested {filename} ({len(chunks)} chunks)")
            return {
                "status": "success",
                "filename": filename,
                "chunks": len(chunks)
            }
        except Exception as e:
            logger.error(f"Ingestion error: {e}")
            return {"status": "failed", "reason": str(e)}
        
    async def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant chunks and return content with metadata."""
        if not self.index:
            return []
            
        try:
            # 1. Ensure embedding model is loaded (non-blocking)
            await self._ensure_embedding_model()
            if not self.embedding_model:
                return []

            # 2. Embed query
            query_vec = await asyncio.to_thread(
                lambda: embed_texts([query], self.embedding_model, show_progress_bar=False)[0]
            )
            
            # 3. Pinecone query
            response = await asyncio.to_thread(
                lambda: self.index.query(
                    vector=query_vec.tolist(),
                    top_k=k,
                    include_metadata=True,
                    namespace=self.index_name
                )
            )
            
            results = []
            for match in response.get("matches", []):
                meta = match.get("metadata", {})
                score = match.get("score", 0.0)
                content = meta.get("text", meta.get("content", meta.get("chunk_text", "")))
                if content:
                    results.append({
                        "id": match.get("id"),
                        "text": content,
                        "score": score,
                        "metadata": meta
                    })
            return results
        except Exception as e:
            logger.error(f"Pinecone Search Error: {e}")
            return []

    def get_stats(self) -> dict:
        if not self.index:
            return {"total_vectors": 0}
        try:
            stats = self.index.describe_index_stats()
            return {"total_vectors": stats.get("total_vector_count", "unknown")}
        except Exception as e:
            logger.error(f"Stats Error: {e}")
            return {"total_vectors": "unknown"}

global_kb = GlobalKnowledgeBase()
