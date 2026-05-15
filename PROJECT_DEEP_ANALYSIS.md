# Legal Research AI — Project Deep Technical Analysis

**Document purpose:** Reverse-engineered, implementation-faithful reference for senior engineers, ML/RAG specialists, and platform operators.  
**Scope:** Entire repository as of analysis generation; behavior inferred from code paths where runtime configuration varies.  
**Repository root:** Modular monorepo with `app/` (FastAPI), `frontend/` (Next.js), `docs/`, `tests/`, `schema.sql`, Docker assets.

\---

## Table of Contents

1. [Executive Overview](#1-executive-overview)
2. [Complete Tech Stack Analysis](#2-complete-tech-stack-analysis)
3. [Full Repository Structure](#3-full-repository-structure)
4. [AI/LLM Architecture Deep Dive](#4-aillm-architecture-deep-dive)
5. [Embedding Pipeline Analysis](#5-embedding-pipeline-analysis)
6. [Chunking Strategy Deep Dive](#6-chunking-strategy-deep-dive)
7. [Retrieval Pipeline Analysis](#7-retrieval-pipeline-analysis)
8. [Prompt Engineering Analysis](#8-prompt-engineering-analysis)
9. [Agent Architecture Analysis](#9-agent-architecture-analysis)
10. [Memory System Analysis](#10-memory-system-analysis)
11. [Database + Vector Store Deep Dive](#11-database--vector-store-deep-dive)
12. [API and Backend Flow](#12-api-and-backend-flow)
13. [Frontend Architecture](#13-frontend-architecture)
14. [Infrastructure + Deployment](#14-infrastructure--deployment)
15. [Performance Optimization Analysis](#15-performance-optimization-analysis)
16. [Security Analysis](#16-security-analysis)
17. [Dependency Analysis](#17-dependency-analysis)
18. [Data Flow Walkthrough](#18-data-flow-walkthrough)
19. [Configuration \& Parameters Master Table](#19-configuration--parameters-master-table)
20. [Code Quality + Architectural Risks](#20-code-quality--architectural-risks)
21. [Recommendations](#21-recommendations)

\---

## 1\. Executive Overview

### What this project does

A **legal-domain research assistant** that:

* Accepts authenticated user queries via a **streaming HTTP (SSE-style)** chat API.
* Classifies intent (**SUMMARY / RESEARCH / GENERAL**).
* For research-like intents, gathers **external web snippets** and/or **internal vector-indexed text**, then produces an answer with **citation-oriented prompting** (RESEARCH) or a **BART-based extractive-style summary** with **sentence-level grounding filters** (SUMMARY).
* Persists **conversations and messages** in **Supabase** when available, with an **in-memory stateless fallback** if DB operations fail.

### Business / domain purpose

High-stakes **legal information retrieval and synthesis** with explicit emphasis on **reducing hallucination** through:

* Retrieval-first context assembly for **RESEARCH**.
* **BART** summarization plus **NLTK sentence** overlap checks against retrieved strings for **SUMMARY**.
* System prompts that demand **markdown links** to sources present in context and **honesty about product capabilities** (`SYSTEM\_CAPABILITY\_CONTEXT`).

### Core architecture style

|Aspect|Style|
|-|-|
|Backend|**Modular monolith** (single FastAPI process, router modules)|
|Frontend|**SPA-style Next.js** (`"use client"` research UI) talking to REST + SSE|
|AI orchestration|**Hand-rolled pipeline** in `ResearchService` (not LangGraph / AutoGen / CrewAI)|
|Data planes|**Supabase** (Postgres + Auth + RLS) + optional **Pinecone** (runtime KB) + **FAISS utilities** (library present; not wired into main chat path)|
|LLM routing|**Ollama** primary (+ optional fallback model in **streaming** path only) → **OpenAI** chat completions if Ollama unavailable and key valid|

### High-level AI workflow

```
User query
  → intent classification (heuristics + optional LLM)
  → (RESEARCH/SUMMARY) query rewrite for search
  → parallel-ish retrieval: web (Tavily|DDG) + Pinecone (if configured)
  → optional mode switch to GENERAL if zero retrieval
  → SUMMARY: BART + grounding filter | RESEARCH: LLM stream with citations | GENERAL: LLM stream
  → persist assistant output (Supabase or RAM fallback)
```

### Inference vs training

* **Inference only** in production paths. **No fine-tuning**, **no training loops**, **no LoRA/PEFT**, **no evaluation harness** beyond `pytest` API/stream tests.

### RAG design

**Yes — hybrid RAG-like**, but important nuance:

* **“RAG”** here = **retrieve text snippets → concatenate as context → LLM generation** (RESEARCH) or **retrieve → BART summarize with grounding filter** (SUMMARY).
* There is **no cross-encoder reranker**, **no multi-query decomposition** in code, **no parent–child chunk hierarchy** in runtime retrieval.

### Agentic patterns

**Lightweight “agent” UX** (status strings like “Agent Logic”) but **no tool-calling framework**: the backend does **fixed procedural steps** (classify → search → assemble prompt → stream). This is closer to a **deterministic pipeline** than an autonomous agent.

### Monolith vs microservices

* **Two deployable units** in Docker Compose: `backend` (FastAPI) + `frontend` (Next.js standalone).
* **Not** decomposed into separate inference/search/auth microservices.

### Deployment style

**Container-first** (`Dockerfile` backend, `frontend/Dockerfile`), **Compose** for local/prod-like single host. **No Kubernetes manifests** and **no CI/CD workflows** under `.github/` in this tree.

\---

## 2\. Complete Tech Stack Analysis

### Technology master table (implementation-grounded)

|Technology|Version (manifest)|Purpose|Primary files|Why chosen (inferred)|
|-|-|-|-|-|
|Python|3.11 (`Dockerfile`)|Backend runtime|`Dockerfile`, `app/\*\*`|Stable ecosystem for PyTorch/ST|
|FastAPI|`>=0.109`|HTTP API, OpenAPI, DI|`app/main.py`, `app/routers/\*\*`|Async-friendly, typed models|
|Uvicorn|`>=0.27`|ASGI server|`Dockerfile` CMD, `docker-compose.yml`|Standard FastAPI deployment|
|Pydantic v2|`>=2.5`|Settings + request/response models|`app/config.py`, `app/models.py`|Validation, env binding|
|Supabase Python|`>=2.3`|Auth + Postgres CRUD|`app/dependencies.py`, `app/services/research.py`|Hosted auth + DB with RLS|
|Sentence-Transformers|`>=2.3`|Dense embeddings|`app/core/embedding\_store.py`|Local embedding without vendor lock-in for vectors|
|PyTorch|`>=2.0`|ST + BART runtime|`embedding\_store.py`, `summarizer.py`|De facto ML runtime|
|Transformers|`>=4.35`|BART `AutoModelForSeq2SeqLM`|`app/core/summarizer.py`|Prebuilt summarization stack|
|FAISS (CPU)|`>=1.7.4`|Local flat L2 index utilities|`app/core/embedding\_store.py`, `app/core/retriever.py`|Offline/batch vector experiments|
|Pinecone client|`>=5.0`|Hosted vector index for `global\_kb`|`app/services/global\_kb.py`|Managed similarity search at scale|
|httpx|`>=0.27`|Async HTTP to Ollama|`app/core/ollama\_utils.py`|Native async streaming|
|OpenAI SDK|`>=1.10`|Fallback LLM|`app/core/ollama\_utils.py`|Cloud fallback when Ollama down|
|requests|`>=2.31`|Tavily + DDG scrape|`app/core/web\_search.py`|Simple blocking HTTP for tools|
|BeautifulSoup4|`>=4.12`|HTML parse for DDG|`app/core/web\_search.py`|Scrape search results without browser|
|NLTK|`>=3.8`|Sentence tokenize + punkt|`app/core/ingestion.py`, `app/core/summarizer.py`|Lightweight sentence segmentation|
|pandas|`>=2.0`|CSV ingestion utilities|`app/core/ingestion.py`|Batch dataset prep|
|langchain-core|`>=0.1.0`|`Document` type for search results|`app/core/web\_search.py`|Thin structural reuse (not full LC agent stack)|
|slowapi|`>=0.1.9`|Rate limits|`app/main.py`, `app/routers/chat.py`, `app/routers/admin.py`|Per-IP throttling|
|Next.js|`16.1.6` (`frontend/package.json`)|UI framework|`frontend/app/\*\*`|SSR/CSR hybrid, standalone output|
|React|`19.2.4`|UI|`frontend/\*\*`|Ecosystem standard|
|TanStack Query|`^5.62`|Server-state cache|`frontend/app/research/page.tsx`|Conversation list invalidation|
|Zustand|`^5.0.2`|Client UI state|`frontend/store/\*.ts`|Minimal global store|
|TypeScript|`5.7.3`|Typed frontend|`frontend/\*\*`|Safety for API contracts|

### Not present (explicit negative findings)

* **No Kubernetes** YAML in repo.
* **No GitHub Actions / GitLab CI** in repo (no `.github/workflows`).
* **No OpenTelemetry / Prometheus / Grafana** instrumentation beyond Python `logging` and FastAPI access-style middleware logging.
* **No dedicated queue** (Redis/Rabbit/SQS) — async is in-process `asyncio`.
* **No GPU-specific Dockerfile** (CPU-oriented `python:3.11-slim`; CUDA optional at runtime if host has drivers + proper torch build, not declared here).

\---

## 3\. Full Repository Structure

### High-level tree (functional, not every UI primitive)

```
.
├── app/                          # FastAPI application package
│   ├── main.py                   # App factory, CORS, limiter, routers, health
│   ├── config.py                 # Pydantic Settings (env-driven)
│   ├── models.py                 # Pydantic API models
│   ├── dependencies.py           # Supabase client + auth dependencies
│   ├── routers/
│   │   ├── auth.py               # signup/login/me/logout
│   │   ├── chat.py               # streaming query + conversation CRUD
│   │   └── admin.py              # ingest + stats (admin-only)
│   ├── services/
│   │   ├── research.py           # Core orchestration pipeline
│   │   ├── global\_kb.py          # Pinecone-backed KB service
│   │   └── cache.py              # In-memory ResearchCache (currently unused in hot path)
│   └── core/
│       ├── assistant\_context.py  # System capability grounding string
│       ├── ollama\_utils.py       # LLM client (Ollama + OpenAI)
│       ├── web\_search.py         # Tavily + DuckDuckGo providers
│       ├── embedding\_store.py    # ST init + embed + FAISS helpers + Pinecone upsert helper
│       ├── ingestion.py          # Cleaning + sentence-aware chunking + CSV preprocessing
│       ├── retriever.py          # Generic Pinecone/FAISS retrieval helpers (not used by research.py)
│       └── summarizer.py         # BART load + generate + grounding filter
├── frontend/                     # Next.js UI
│   ├── app/                      # Routes (research, login, signup, admin)
│   ├── components/               # UI + chat components
│   ├── services/                 # api-client + domain services
│   ├── store/                    # Zustand stores
│   └── types/api.ts              # Shared TS contracts
├── tests/                        # pytest (API + streaming mocks)
├── docs/                         # Human-written API/deployment docs (may drift from code)
├── schema.sql                    # Supabase-oriented SQL (pgvector + conversations)
├── docker-compose.yml            # Backend + frontend stack
├── Dockerfile                    # Backend image
├── download\_models.py            # Pre-cache HF models + NLTK
├── requirements.txt              # Python deps (ranges, not locked)
├── legacy/                       # Older scripts (not on hot path)
└── explanation/                  # Narrative system guide (non-executable)
```

### Folder purposes

|Path|Purpose|
|-|-|
|`app/`|All production backend logic; clear split routers/services/core.|
|`app/services/research.py`|**Single orchestration brain** for user-visible research behavior.|
|`app/services/global\_kb.py`|Optional Pinecone ingestion/search; **disabled** without API key.|
|`app/core/retriever.py`|Reusable retrieval primitives; **not imported** by `research.py` (dead for main flow).|
|`frontend/`|Complete UI; uses `NEXT\_PUBLIC\_API\_URL` for backend.|
|`schema.sql`|Canonical **Supabase SQL** for profiles, `documents`+pgvector, conversations — **partially overlapping** with Pinecone KB approach.|
|`tests/`|FastAPI `TestClient` + mocks; not load-testing ML.|

\---

## 4\. AI/LLM Architecture Deep Dive

### Models and providers (actual code defaults)

|Role|Model ID (default in code)|Provider|Where defined|Notes|
|-|-|-|-|-|
|Embeddings|`BAAI/bge-large-en-v1.5`|HuggingFace / local ST|`app/core/embedding\_store.py` `initialize\_embedding\_model()`|Device auto: CUDA if available else CPU|
|Summarization|`facebook/bart-large-cnn`|HuggingFace Transformers|`app/core/summarizer.py` `load\_summarization\_model()`|Seq2seq, beam search generation|
|Primary chat LLM|`settings.OLLAMA\_MODEL` default **`gemma2:9b`**|Ollama|`app/config.py`|Local inference server|
|Fallback chat LLM (stream only)|`settings.OLLAMA\_FALLBACK\_MODEL` default **`gemma2:2b`**|Ollama|`app/config.py`|Used only in `generate\_stream` loop|
|Cloud LLM fallback|`settings.OPENAI\_MODEL` default **`gpt-3.5-turbo`**|OpenAI|`app/config.py`|Chat Completions API|
|Intent / query rewrite|Same primary Ollama model|Ollama|`OllamaClient.generate()`|**Does not iterate fallback models** (see risks)|

### Embedding dimensions (critical consistency note)

* `schema.sql` declares `embedding vector(768)` for `public.documents` and `match\_documents`.
* The configured embedding model is **`BAAI/bge-large-en-v1.5`**, which in standard HuggingFace/Sentence-Transformers distributions is **1024-dimensional** for the “large” English variant (while **base** models are often 768-d).
* **Uncertainty:** If you intended `768`, the codebase default model may be **misaligned** with the SQL artifact. If you use Pinecone, the index dimension must match the model output regardless of SQL.

### BART generation parameters (grounded summarization)

From `generate\_summary\_with\_guardrails`:

|Parameter|Default|Meaning|
|-|-|-|
|`max\_input\_length`|1024|Truncate tokenized prompt to this many tokens|
|`max\_length`|150|Max generated summary tokens|
|`min\_length`|50|Min summary tokens|
|`num\_beams`|4|Beam search width|
|`no\_repeat\_ngram\_size`|3|Blocks repeating trigrams|
|CPU beam reduction|`min(num\_beams, 2)`|Speed tradeoff on CPU|

**Why:** Beam search + `no\_repeat\_ngram\_size` reduces degenerate repetition; CPU lowers beams to control latency.

### Grounding filter (post-hoc, heuristic)

After BART decode, each sentence must pass:

* Full lowered sentence substring contained in any lowered chunk, **OR**
* Any token with `len(word) > 3` appears in a chunk.

**Tradeoff:** High recall for “some overlap exists” but **false positives** (generic legal words matching wrong chunk) and **false negatives** (paraphrased correct facts removed).

### LLM streaming stack

`OllamaClient.generate\_stream`:

1. `GET {OLLAMA\_BASE\_URL}/api/tags` with **3s** timeout to mark Ollama up/down.
2. Try `OLLAMA\_MODEL`, then `OLLAMA\_FALLBACK\_MODEL` using `/api/generate` with `stream: true`, line-delimited JSON chunks; read `response` field until `done`.
3. If both fail, optionally OpenAI **streaming** chat completions.

`OllamaClient.generate` (non-stream):

* Uses **only** `self.model` (no fallback loop) with **60s** timeout.
* On failure → OpenAI non-stream.

\---

## 5\. Embedding Pipeline Analysis

### Initialization

```22:44:app/core/embedding\_store.py
def initialize\_embedding\_model(
    model\_name: str = 'BAAI/bge-large-en-v1.5',
    device: Optional\[str] = None
) -> SentenceTransformer:
    if device is None:
        device = "cuda" if torch.cuda.is\_available() else "cpu"
    logger.info(f"Loading embedding model: {model\_name} on {device}...")
    model = SentenceTransformer(model\_name, device=device)
```

**Implications:**

* First query paying **cold-start model download** unless `download\_models.py` or Docker layer caching warmed HF cache (`HF\_HOME` set in backend `Dockerfile`).

### Encoding

```47:72:app/core/embedding\_store.py
def embed\_texts(
    texts: List\[str],
    model: SentenceTransformer,
    convert\_to\_numpy: bool = True,
    show\_progress\_bar: bool = True
) -> np.ndarray:
    embeddings = model.encode(
        texts,
        convert\_to\_numpy=convert\_to\_numpy,
        show\_progress\_bar=show\_progress\_bar
    )
```

**Batching:** ST `encode` will batch internally; callers often pass whole chunk lists from ingestion.

**Normalization / similarity metric:**

* Pinecone index metric is determined at **index creation time in Pinecone cloud** (not in-repo). `global\_kb` queries with raw embedding list; **cosine vs dot** depends on hosted index config — **not enforced in code**.
* FAISS path uses **`IndexFlatL2`** on **raw** ST vectors in `create\_or\_load\_faiss\_index` — for ST models, **inner-product / cosine** is more typical; L2 on non-normalized vectors is a **semantic distance choice** that may or may not match training normalization.

### Pinecone upsert helper (batch/metadata limits)

```148:212:app/core/embedding\_store.py
def upsert\_documents(
    index: Any,
    chunk\_texts: List\[str],
    chunk\_embeddings: np.ndarray,
    document\_ids: List\[str],
    namespace: str = "",
    batch\_size: int = 100,
    metadata\_text\_limit: int = 1000
) -> Dict\[str, Any]:
```

**Note:** `create\_or\_connect\_pinecone\_index` in the same module **raises `RuntimeError`** (“disabled in this build”) — operational Pinecone wiring is in `global\_kb.py` using `Pinecone(api\_key=...)`.

### Lazy loading + concurrency locks

Both `ResearchService` and `GlobalKnowledgeBase` lazy-load the embedding model behind `asyncio.Lock` to avoid duplicate loads under concurrency.

\---

## 6\. Chunking Strategy Deep Dive

### Algorithm type

**Sentence-bounded word-count chunking with overlap**, implemented in `chunk\_text`:

```47:99:app/core/ingestion.py
def chunk\_text(text: str, chunk\_size: int = 250, overlap: int = 40) -> List\[str]:
    sentences = nltk.sent\_tokenize(text)
    ...
    if current\_chunk\_word\_count + sentence\_word\_count > chunk\_size and current\_chunk\_word\_count > 0:
        chunks.append(" ".join(current\_chunk\_sentences))
        # overlap: walk backwards through sentences until \~overlap words
```

### Parameters

|Parameter|Default|Unit|Meaning|
|-|-|-|-|
|`chunk\_size`|250|**words** (approx; sentence-bounded)|Target max words per chunk before flush|
|`overlap`|40|**words** (approx)|Carry sentences/words into next chunk|

### What it is *not*

* Not **recursive character** splitting (LangChain `RecursiveCharacterTextSplitter`).
* Not **semantic** chunking (no embedding-space boundaries).
* Not **token-based** (no tiktoken); uses whitespace word splits inside sentences.
* Not **markdown-aware** or **code-aware** (no header hierarchy parsing).

### Where used

* `GlobalKnowledgeBase.ingest\_document` uses `chunk\_text(content, chunk\_size=250, overlap=40)`.
* `preprocess\_documents` applies same defaults for CSV pipelines.

### Quality / hallucination interactions

* **Pros:** Respects sentence boundaries → fewer mid-sentence cuts → better readability in retrieved snippets.
* **Cons:** Long single sentences can blow chunk budget; legal citations may be separated from the sentences they support depending on segmentation.
* **Overlap 40 words:** mitigates boundary effects for retrieval; increases **storage redundancy** (more vectors per doc).

\---

## 7\. Retrieval Pipeline Analysis

### Orchestrated retrieval (production chat)

Implemented **inline** in `ResearchService.run\_research\_stream` rather than via `retriever.py`.

#### Web retrieval

* Provider selection: `create\_web\_search\_tool()` in `web\_search.py`:

  * Tavily if `TAVILY\_API\_KEY` env set (or explicit factory args).
  * Else **DuckDuckGo HTML POST** scraper.

```175:192:app/core/web\_search.py
def create\_web\_search\_tool(
    provider: str = None, # Auto-detect
    api\_key: Optional\[str] = None
) -> BaseWebSearch:
    env\_key = os.getenv("TAVILY\_API\_KEY")
    if env\_key:
        return TavilySearch(env\_key)
    return DuckDuckGoSearch()
```

**Tavily payload constants:**

* `max\_results` passed from caller (`research.py` uses **5**).
* `search\_depth`: **`"basic"`** (cost/latency vs quality tradeoff).
* `include\_answer`: **False** (forces traditional snippet retrieval rather than Tavily-generated answer).

#### Internal vector retrieval (`global\_kb.search`)

```99:137:app/services/global\_kb.py
async def search(self, query: str, k: int = 5) -> List\[Dict\[str, Any]]:
    ...
    response = await asyncio.to\_thread(
        lambda: self.index.query(
            vector=query\_vec.tolist(),
            top\_k=k,
            include\_metadata=True,
            namespace=self.index\_name
        )
    )
```

**Important:** `namespace=self.index\_name` uses the **index name string as Pinecone namespace** — unusual vs typical `"default"` or per-tenant namespaces. Must match how vectors were upserted.

#### Gating threshold (application-level)

```271:279:app/services/research.py
internal\_results = await global\_kb.search(search\_query)
for res in internal\_results:
    score = res.get("score", 0.0)
    if score >= 0.75:
        ...
```

**Interpretation:** Pinecone scores are metric-dependent; treating **`0.75` as universal** assumes index configuration where scores are comparable (often cosine similarity in `\[0,1]`). If metric is dot-product on unnormalized vectors, threshold semantics shift — **treat as tunable constant**, not physical cosine without verification.

#### Web “similarity” field (synthetic)

```263:264:app/services/research.py
sources\_consulted.append({..., "similarity": 0.95, "source\_type": "web"})
```

This is **not** computed semantic similarity; it’s a **UI/API placeholder**.

#### No reranking, no query fusion

* No cross-encoder rerank.
* No BM25 hybrid with dense fusion (DDG is not inverted-index BM25 over your corpus; it’s external web ranking).

#### Empty retrieval behavior

```282:285:app/services/research.py
if not retrieved\_texts:
    intent = "GENERAL"
```

If **both** branches fail or return nothing, pipeline **downgrades** to general LLM knowledge (explicitly logged).

\---

## 8\. Prompt Engineering Analysis

### Categories and locations

|Category|Location|Mechanism|
|-|-|-|
|Capability / anti-hallucination (product truth)|`app/core/assistant\_context.py`|Constant `SYSTEM\_CAPABILITY\_CONTEXT` injected into RESEARCH + GENERAL system prompts|
|Intent classification|`app/services/research.py` `\_classify\_intent`|LLM prompt with strict system: single word|
|Query optimization|`\_get\_optimized\_search\_query`|LLM converts user text to search query|
|RESEARCH system prompt|`run\_research\_stream`|Mandates markdown links, paragraph spacing, integrity|
|GENERAL system prompt|`run\_research\_stream`|“General knowledge” + capability honesty|
|BART summarization instruction|`app/core/summarizer.py`|Prepended “Please summarize…” string|

### Full capability grounding string (abridged reference)

See file `app/core/assistant\_context.py` — it enumerates **actual** tools: Tavily/DDG, Pinecone KB, BART path, Supabase memory, SSE streaming, admin APIs, stack facts, and explicit **“do not invent tools”** instructions.

### RESEARCH system prompt (core rules)

```309:319:app/services/research.py
system\_prompt = f"""You are an elite Legal Research Assistant.
\*\*STRICT CITATION RULES:\*\*
1. \*\*Mandatory Links:\*\* For every case, law, or fact you provide from the context, you MUST include a clickable markdown link in the format: \[Source Name]({{'URL'}}).
...
{SYSTEM\_CAPABILITY\_CONTEXT}

{history\_str}"""
```

**Issues to note:**

* The example link syntax contains **`{{'URL'}}`** which is likely a **templating mistake** (should illustrate real markdown). Models often still output valid links from context, but this is **prompt noise / confusion risk**.

### Intent classification prompt

```116:129:app/services/research.py
prompt = f"""Task: Classify the user's intent.
Categories:
- 'SUMMARY': ...
- 'RESEARCH': ...
- 'GENERAL': ...
...
Category:"""
resp = await self.ollama.generate(prompt, system="Output exactly ONE word: \[SUMMARY, RESEARCH, or GENERAL].")
```

**Robustness:** Parser checks substring containment in model output; on exception defaults to **`RESEARCH`**.

### Variable injection

* **History:** last N messages string from DB/stateless (`limit=10` in `get\_conversation\_history`).
* **Context:** `"\\n\\n".join(retrieved\_texts)` where each item is markdown-ish lines built from web/internal hits.

### No separate “tool JSON” / function calling

Ollama path uses `/api/generate` with `prompt` + optional `system`, not OpenAI-style tool schemas.

\---

## 9\. Agent Architecture Analysis

### Framework

**None** (no LangGraph agent, no AutoGen agents).

### Tooling model

Hard-coded calls:

* `self.web\_search\_provider.search(...)`
* `await global\_kb.search(...)`

### Planning / reflection

* **No iterative plan–execute loop.**
* **No self-critique** pass on final answer.
* **SUMMARY** uses BART + rule-based sentence filter only.

### Routing logic

1. Heuristic capability detection → GENERAL.
2. Heuristic trivial short query → GENERAL.
3. Keyword-based legal detection → RESEARCH (short-circuit).
4. Else LLM classifier.
5. Post-retrieval empty-context → GENERAL.

### State

* Conversation state in **Supabase** tables (`conversations`, `messages`) with **stateless RAM** fallback keyed by conversation id.

\---

## 10\. Memory System Analysis

### Short-term (within request)

* Streaming accumulates `full\_answer` string before DB write.
* `retrieved\_texts` only lives for the duration of the request.

### Conversation memory (multi-turn)

|Mechanism|Implementation|Limits|
|-|-|-|
|DB-backed|Supabase inserts/selects|`get\_conversation\_history(..., limit=10)`|
|Stateless fallback|`ResearchService.stateless\_conversations` dict|**Process-local**, lost on restart; not sharded|

### Vector memory (long-term knowledge)

* **Pinecone** (if API key present) holds embedded chunks from admin ingestion path.
* **Supabase `documents` + pgvector** exists in `schema.sql` but **no runtime query** in `research.py` to `match\_documents` RPC was found — **second vector store path is currently non-integrated** in orchestration.

### Summarization for memory compression

* No rolling summarization of old turns; only last **10** messages concatenated.

### Eviction

* Stateless dict grows without LRU for conversations list (only message append per conversation).
* `ResearchCache` implements TTL + max size eviction — **but unused** in `research.py` hot path (import only).

\---

## 11\. Database + Vector Store Deep Dive

### Supabase / Postgres (runtime)

**Tables used in Python:**

* `conversations` insert/select/delete (`research.py`)
* `messages` insert/select (`research.py`)
* `profiles` select for role (`dependencies.py`)

### Supabase SQL artifact (`schema.sql`)

Includes:

* `profiles` with roles `user|admin`.
* `documents` with `embedding vector(768)` + RLS policies.
* `match\_documents(query\_embedding vector(768), match\_threshold float, match\_count int)` using cosine distance operator **`<=>`** and `1 - distance` as similarity.

**Integration gap:** Application orchestration does **not** call this RPC in `research.py`.

### Pinecone (runtime KB)

* Connection when `PINECONE\_API\_KEY` set.
* Upsert metadata includes `text`, `title`, `filename`, `created\_at`.
* Query returns matches; app reads `metadata.text` primarily.

### Namespace / index naming coupling

Upsert and query both use `namespace=self.index\_name` where `index\_name` defaults to **`legal-case-rag-advanced`** — coupling index identifier with namespace.

\---

## 12\. API and Backend Flow

### Endpoints (routers + core)

|Method|Path|Auth|Rate limit|Purpose|
|-|-|-|-|-|
|POST|`/auth/signup`|No|—|Supabase signup; may warm models in background|
|POST|`/auth/login`|No|—|Supabase login; may warm models|
|GET|`/auth/me`|Bearer|—|Profile|
|POST|`/auth/logout`|No|—|Symmetry noop|
|POST|`/chat/query`|Bearer|**10/min** (`slowapi`)|SSE streaming research|
|GET|`/chat/conversations`|Bearer|—|Merge DB + stateless|
|GET|`/chat/conversation/{id}`|Bearer|—|Thread detail|
|DELETE|`/chat/conversation/{id}`|Bearer|—|Delete thread|
|POST|`/admin/ingest`|Admin|**5/min**|Upload text → Pinecone pipeline|
|GET|`/admin/stats`|Admin|—|Pinecone stats|
|GET|`/`|No|—|Meta|
|GET|`/health`|No|—|Liveness|
|GET|`/info`|No|—|Non-secret diagnostics|

### Streaming protocol (actual)

`chat.py` wraps non-JSON chunks as:

```47:48:app/routers/chat.py
yield f"data: {json.dumps({'token': chunk})}\\n\\n"
```

Metadata JSON lines forwarded raw as `data: {...}\\n\\n`. Terminal `data: \[DONE]\\n\\n`.

### Request lifecycle (chat)

1. `slowapi` limiter applied via nested function pattern.
2. `get\_current\_user` validates Supabase JWT (or test bypass).
3. `research\_service.run\_research\_stream` yields chunks consumed by SSE generator.

### Async jobs

* `BackgroundTasks` on auth success to `\_ensure\_embedding\_model` and `\_ensure\_summarizer\_loaded` — **warms** heavy models after login/signup.

### Webhooks / events

**None** in codebase.

\---

## 13\. Frontend Architecture

### State management

* **Zustand** stores: `auth-store`, `chat-store`.
* **TanStack Query** used for cache invalidation of conversation list on new `conversation\_id`.

### Streaming UI

`frontend/app/research/page.tsx`:

* Calls `streamChatQuery` → `createStreamingRequest` parses SSE `data:` lines.
* Handles `sources`, `conversation\_id`, `token`, errors, `\[DONE]`.

### SSR/CSR

Research page is **`"use client"`** — CSR-heavy; no RSC streaming of LLM tokens from Next server.

### Data fetching

* Plain `fetch` to `${NEXT\_PUBLIC\_API\_URL}` (see `frontend/services/api-client.ts`).

### Component architecture

* Chat presentation split: `chat-input`, `chat-message`, `source-card`, `conversation-sidebar`.
* Large `components/ui/\*` set is a **design system layer** (Radix-based patterns).

\---

## 14\. Infrastructure + Deployment

### Docker

* **Backend:** multi-stage Python slim; non-root `appuser`; NLTK baked; HF cache dir; healthcheck `curl /health`.
* **Compose:** pins **single uvicorn worker** (avoid duplicate in-memory ML), `huggingface\_cache` volume, `host.docker.internal` mapping for Ollama on Linux engines.
* **Frontend:** Node 22 Alpine, `output: "standalone"`, non-root `nextjs`, `HOSTNAME=0.0.0.0`.

### Kubernetes

**None.**

### CI/CD

**None** in repo.

### Environment variables (backend)

From `app/config.py` + `.env.example`:

* **Required for boot:** `SUPABASE\_URL`, `SUPABASE\_KEY`
* **LLM:** `OLLAMA\_\*`, `OPENAI\_\*`
* **Vectors:** `PINECONE\_API\_KEY` optional; `PINECONE\_INDEX\_NAME`
* **CORS:** `CORS\_ORIGINS`
* **Web:** `TAVILY\_API\_KEY` optional (also read directly in `web\_search.py` via `os.getenv`)

### Secrets management

* `.env` file for local/docker compose (gitignored in healthy setups).
* No Vault/KMS integration in code.

### GPU requirements

* Not required; **CPU fallback** everywhere. GPU improves latency if CUDA-enabled torch installed on host image (not shown in Dockerfile beyond base torch wheel).

### Scaling strategy

* Vertical scaling of single container is the practical path due to **large in-process models**.
* Multi-replica deployment requires **externalizing** models or accepting duplicated RAM — not addressed here.

### Monitoring / telemetry

* Python logging + request middleware logs path + status.
* `@vercel/analytics` present in frontend dependencies (product analytics), not backend traces.

\---

## 15\. Performance Optimization Analysis

|Optimization|Where|Why|
|-|-|-|
|Lazy model loading|`research.py`, `global\_kb.py`|Avoid multi-minute startup blocking FastAPI boot|
|`asyncio.to\_thread` for CPU inference|embedding + BART calls|Keep event loop responsive|
|Locks around lazy init|`\_embed\_lock`, `\_sum\_lock`|Prevent thundering herd duplicate loads|
|Reduced beams on CPU|`summarizer.py`|Cut generation latency|
|HF cache directory|`Dockerfile` env|Speed repeated container restarts|
|Background warm on auth|`auth.py`|Shift load to post-login idle|
|Tavily `search\_depth=basic`|`web\_search.py`|Reduce API cost/time vs advanced|
|DDG timeout 10s|`web\_search.py`|Bound worst-case latency|

\---

## 16\. Security Analysis

### Strengths

* Supabase JWT validation for protected routes.
* Admin routes gated by `profiles.role == admin`.
* `TESTING` auth bypass cannot be enabled via `.env` (only programmatic).

### Risks / gaps

|Risk|Detail|
|-|-|
|SSRF / URL exfiltration|Ollama URL configurable; must be trusted network only|
|HTML scraping fragility|DuckDuckGo HTML changes can break search; not a security boundary but availability|
|Prompt injection|Retrieved web pages/snippets are concatenated into LLM context with minimal structural sanitization|
|RAG poisoning|If Pinecone ingest is compromised, retrieved content drives answers — **admin upload** is the trust boundary|
|JWT secret|Default secret triggers critical log in prod config — must rotate|
|Rate limits|Per-IP only; distributed attackers can bypass with many IPs|
|`/info`|Exposes config hints (`ollama\_url`, model names) — minor recon|

\---

## 17\. Dependency Analysis

### Critical libraries

* **torch + transformers + sentence-transformers:** core ML footprint (image size, RAM).
* **pinecone:** optional but required for internal KB path.
* **supabase:** auth + persistence.
* **httpx / openai:** LLM networking.

### Declared but lightly / inconsistently used

* **`duckduckgo-search`** in `requirements.txt` but **web\_search.py** uses `requests`+BeautifulSoup, not the `duckduckgo\_search` package — **possible dead dependency**.
* **`ollama` PyPI package** in requirements; client uses raw HTTP — **may be unused**.

### Risk notes

* Open ranges in `requirements.txt` → **non-reproducible builds** unless locked elsewhere.
* `grpcio` pins often accompany Pinecone; keep compatible with `pinecone` major.

### ASCII dependency sketch

```
Browser (Next.js)
  --HTTPS--> FastAPI
               ├--> Supabase (JWT + CRUD)
               ├--> Ollama HTTP (/api/generate)
               ├--> OpenAI HTTPS (fallback)
               ├--> Tavily HTTPS OR DuckDuckGo HTML
               ├--> Pinecone (optional)
               └--> Local CPU/GPU torch for ST + BART
```

\---

## 18\. Data Flow Walkthrough

### End-to-end: authenticated HYBRID research query

1. **User input** in `frontend/app/research/page.tsx` → `streamChatQuery`.
2. **HTTP POST** `/chat/query` with JSON `{query, scope, conversation\_id?}` + bearer token.
3. **Auth:** `dependencies.get\_current\_user` validates token + loads role.
4. **Rate limit:** `10/min` per IP for chat query route.
5. **Conversation ensure:** insert conversation row or create stateless id (`research.py`).
6. **Persist user message** (unless filtered).
7. **Intent:** heuristics + optional Ollama classification.
8. **SSE metadata:** first JSON `{sources:\[], conversation\_id, intent}`.
9. **Status tokens:** human-readable progress strings (not JSON).
10. **Query rewrite:** Ollama `generate` → optimized search string.
11. **External retrieval (if scope allows):** Tavily or DDG up to **5** results; append markdown lines into `retrieved\_texts`.
12. **Internal retrieval (if scope allows):** Pinecone top **5** matches; filter `score >= 0.75`; append markdown lines.
13. **If empty:** switch intent to GENERAL.
14. **Else:** second metadata JSON with sources list filtered to `http` URLs (drops `#` internal placeholders).
15. **History string:** up to **10** prior messages.
16. **Generation:**

    * **SUMMARY** with nonempty retrieval: load BART if needed; call `generate\_summary\_with\_guardrails` where `grounded\_context` is **`query + "\\n\\n" + joined(retrieved\_texts)`** (note: function name vs actual concatenation order).
    * **RESEARCH:** stream tokens from LLM with citation system prompt + context.
    * **GENERAL:** stream with general system prompt.
17. **Persistence:** assistant message saved to Supabase or stateless dict.
18. **SSE termination:** `\[DONE]`.

\---

## 19\. Configuration \& Parameters Master Table

> Values are \*\*defaults\*\* unless overridden by environment. “Impact” is directional.

|Parameter|Value|File|Purpose|Impact|Recommendation|
|-|-|-|-|-|-|
|`OLLAMA\_MODEL`|`gemma2:9b`|`app/config.py`|Primary local LLM|Quality/latency/hardware|Match installed Ollama models|
|`OLLAMA\_FALLBACK\_MODEL`|`gemma2:2b`|`app/config.py`|Secondary try in **stream** only|Resilience|Align `generate()` with same fallback policy|
|`OPENAI\_MODEL`|`gpt-3.5-turbo`|`app/config.py`|Cloud fallback|Cost/capability|Consider `gpt-4o-mini` for cost/quality tradeoff|
|Ollama availability timeout|`3.0s`|`ollama\_utils.py`|Probe `/api/tags`|False negatives on slow nets|Tune if flaky|
|Ollama generate timeout|`60.0s`|`ollama\_utils.py`|Non-stream calls|Long jobs vs failures|Add streaming for classify if needed|
|Web `max\_results`|`5`|`research.py`|Result count|Recall vs context size|Raise cautiously (context bloat)|
|Internal `k`|`5`|`global\_kb.py` `search()`|Pinecone top\_k|Recall|Tune per index size|
|Internal similarity gate|`0.75`|`research.py`|Filter weak matches|Precision/recall|Validate against Pinecone metric|
|Web similarity display|`0.95` constant|`research.py`|UI only|Misleading UX|Compute real score or omit|
|History `limit`|`10`|`research.py`|Turns in prompt|Context length|Balance vs model window|
|Chunk `chunk\_size`|`250` words|`ingestion.py`, `global\_kb.py`|Vector granularity|Retrieval quality|A/B with 200–400|
|Chunk `overlap`|`40` words|`ingestion.py`|Boundary continuity|Storage|Tune with chunk\_size|
|Pinecone upsert batch|`50`|`global\_kb.py`|RPC batching|Throughput|Increase if rate-limits allow|
|Pinecone upsert batch (helper)|`100`|`embedding\_store.py`|Batch upsert helper|Throughput|Keep consistent|
|Metadata text limit|`1000` chars|`embedding\_store.py`|Pinecone metadata size|Truncation loss|Raise if snippets too short|
|BART `max\_input\_length`|`1024` tokens|`summarizer.py`|Input cap|Information loss|Align with mean retrieved size|
|BART `max\_length`|`150`|`summarizer.py`|Output cap|Answer brevity|Legal summaries may need more|
|BART `min\_length`|`50`|`summarizer.py`|Output floor|Verbosity|—|
|BART `num\_beams`|`4` (2 CPU)|`summarizer.py`|Search quality|Latency|GPU keeps 4|
|`no\_repeat\_ngram\_size`|`3`|`summarizer.py`|Anti-repetition|Diversity|—|
|Chat rate limit|`10/min`|`chat.py`|Abuse control|UX for power users|User-tier limits|
|Admin ingest limit|`5/min`|`admin.py`|Abuse control|Ops throughput|—|
|ResearchCache TTL|`60 min`|`cache.py`|Cached answers|**Unused** in stream path|Wire in or delete|
|JWT expiration|`1440` min|`config.py`|Session lifetime|Security vs UX|Lower for high security|
|`LOG\_LEVEL`|`INFO`|`config.py`|Verbosity|Ops noise|`DEBUG` temporarily|

\---

## 20\. Code Quality + Architectural Risks

### Technical debt / inconsistencies

1. **`research\_cache` imported but unused** in `research.py` — dead code path; misleading for operators expecting caching.
2. **`retriever.py` unused** by orchestrator — duplicate abstraction vs `global\_kb` + inline retrieval.
3. **Supabase pgvector schema** vs **Pinecone runtime** — two vector stories; only one is live.
4. **`embedding\_store.create\_or\_connect\_pinecone\_index` disabled** while `global\_kb` uses Pinecone — confusing module responsibilities.
5. **Admin router docstring** claims “ingestion disabled” but handler still calls `ingest\_document` — docs/behavior mismatch; stats model always `ingestion\_enabled=True`.
6. **Ollama `generate` lacks fallback model iteration** unlike `generate\_stream` — classification can fail when primary model broken but fallback would work in streaming.
7. **Prompt typo** `\[Source Name]({{'URL'}})` undermines citation instruction clarity.
8. **README vs config:** README mentions different fallback chain models than `config.py` defaults — documentation drift risk.
9. **Potential embedding dimension mismatch** between SQL (`768`) and `bge-large-en-v1.5` (typically **1024**) if Supabase path activated without schema update.

### Scalability bottlenecks

* In-process **multi-GB** models per worker.
* Stateless conversation dict not shardable.
* Blocking Tavily/DDG requests run in async methods without `to\_thread` — can block event loop under load (`research.py` calls `self.web\_search\_provider.search` directly).

### AI hallucination risks (residual)

* GENERAL mode after retrieval failure may answer **without citations** while user expected grounded law.
* RESEARCH mode still depends on **LLM faithfully citing**; no automated citation verifier.
* BART grounding filter is **lexical overlap**, not entailment modeling.

### Cost risks

* OpenAI fallback on misconfigured Ollama probes can incur charges.
* Pinecone + Tavily usage scales with traffic.

### Concurrency

* Lazy-load locks are good; however **single writer** persistence patterns to Supabase still race at application level if multiple workers were used (Compose now uses 1 worker — mitigated).

\---

## 21\. Recommendations

### Performance

* Offload blocking `web\_search\_provider.search` to `asyncio.to\_thread` (or httpx async for Tavily).
* Consider **quantized** embedding model or hosted embeddings API if CPU latency dominates.
* If keeping Pinecone, **prewarm** models at container start for predictable latency (trade memory).

### Retrieval quality

* Add **cross-encoder reranking** on top-k internal + external candidates.
* Replace synthetic web similarity with **real scores** (Tavily score) or omit.
* Implement **true hybrid** BM25 over ingested corpus if legal corpus is static enough.

### Chunking

* For long judgments, evaluate **hierarchical chunks** (section → paragraph) with stored parent metadata.

### Architecture

* **Either** wire `research.py` to Supabase `match\_documents` **or** delete/relocate unused SQL to avoid dual-vector confusion.
* Consolidate Pinecone connection helpers; remove dead `RuntimeError` stub or gate imports clearly.

### Security / safety

* Sanitize / structure external web text (length limits per source, HTML strip) before LLM context.
* Add **document ACLs** in vector metadata if multi-tenant legal corpora are introduced.

### Code hygiene

* Remove unused imports (`research\_cache`) or integrate caching consciously (cache key should include user + conversation + scope + time).
* Fix citation prompt example and align `generate()` with streaming fallback policy.

\---

## Appendix A — Fine-tuning / training / evaluation

* **Fine-tuning:** not implemented.
* **Training scripts:** none.
* **Evaluation:** `tests/test\_chat\_stream.py` validates SSE framing; not retrieval accuracy evaluation.

## Appendix B — “Hidden configs”

* Docker build args / compose envs are “hidden” runtime configuration surfaces — see `docker-compose.yml`, `frontend/Dockerfile` `ARG NEXT\_PUBLIC\_API\_URL`.
* No `.cursor` rules in repo required for runtime.

\---

**End of document.**  
If you want this analysis kept in sync with the repo, treat it as a living document: update Section 11 whenever `research.py` gains Supabase vector queries, and update Section 19 whenever `config.py` defaults change.

