# Legal Research AI — Hallucination Mitigation System

> A production-grade, full-stack AI Legal Research Assistant that actively mitigates LLM hallucinations using a multi-layer retrieval, grounding, and verification pipeline — built for high-stakes, accuracy-critical domains.

---

## 📌 Project Overview

This system answers legal queries using **verified, source-cited information** from a hybrid knowledge base, combating the #1 problem with LLMs in production: **hallucination**. It combines Retrieval-Augmented Generation (RAG), extractive summarization with grounding enforcement, and a resilient multi-provider LLM fallback chain — all served over a containerized FastAPI backend with a Next.js frontend.

---

## 📊 Key Technical Metrics

| Metric | Value |
|---|---|
| **Embedding Model** | `BAAI/bge-large-en-v1.5` — 768-dimensional dense vectors |
| **Vector Similarity Gate** | ≥ **0.75** cosine similarity required for retrieval acceptance |
| **Summarizer** | `facebook/bart-large-cnn` — Beam Search (4 beams), n-gram penalty (size=3) |
| **Summarizer Context Window** | 1,024 input tokens → 50–150 token grounded output |
| **Web Sources per Query** | Up to **5 concurrent** external sources via DuckDuckGo |
| **LLM Fallback Chain** | **3 layers**: Qwen3:4b → LLaMA 3.1:8b → GPT-3.5-Turbo |
| **Batch Vector Upsert** | 100 vectors/batch with pre/post namespace statistics |
| **Rate Limiting** | Per-IP enforcement via SlowAPI middleware |
| **API Endpoints** | 13 REST endpoints across Auth, Chat, and Admin routers |
| **Vector Index** | Supabase pgvector / Pinecone (Configurable) |
| **Dependencies** | 47 production packages across AI, vector DB, web, and auth layers |

---

## 🏗️ Hallucination Mitigation Pipeline

```
User Query
    │
    ▼
┌─────────────────────────────┐
│  Intent Classification      │  ← LLM few-shot (SUMMARY / RESEARCH / GENERAL)
└──────────────┬──────────────┘
               │
    ┌──────────▼──────────┐
    │   Query Optimizer   │  ← LLM rewrites query for search engines
    └──────────┬──────────┘
               │
    ┌──────────▼──────────────────────────┐
    │     Hybrid Retrieval Engine         │
    │  ├── DuckDuckGo Web Search (≤5)     │  ← External real-time sources
    │  └── Supabase pgvector (≥0.75 sim.) │  ← Internal vector KB
    └──────────┬──────────────────────────┘
               │
    ┌──────────▼──────────────────────────┐
    │   Hallucination Guard Layer         │
    │  ├── BART Extractive Summarization  │  ← Grounded, source-anchored
    │  └── Sentence-Level Grounding Check │  ← NLTK filters unanchored tokens
    └──────────┬──────────────────────────┘
               │
    ┌──────────▼──────────────────────────┐
    │   LLM Response (Streaming)          │
    │  ├── Mandatory citation enforcement │  ← Clickable markdown links
    │  └── Conversation history context   │  ← Last 10 turns via Supabase
    └─────────────────────────────────────┘
```

---

## 🌟 Features

- **3-Layer Hallucination Mitigation**: RAG retrieval gate (≥0.75 cosine) + BART grounding + mandatory source citation in every response
- **Hybrid Knowledge Retrieval**: Fuses Supabase pgvector (IVFFlat), FAISS local store, and live web search per query
- **Resilient LLM Fallback Chain**: Qwen3 → LLaMA 3.1:8b → GPT-3.5-Turbo with async streaming throughout
- **Sentence-Level Grounding Verification**: NLTK tokenizes BART output; unanchored sentences are filtered before delivery
- **Intent-Aware Routing**: Automatically classifies queries as SUMMARY / RESEARCH / GENERAL and routes to the correct pipeline
- **Thread-Safe Caching**: In-memory cache with async lock guards for embedding and summarizer model loading
- **JWT Authentication**: Supabase Auth with Row Level Security (RLS) policies
- **Docker Ready**: Backend and frontend are containerized separately for production deployment
- **Automated Testing**: Full Pytest suite with `pytest.ini` configuration
- **Full-Stack**: FastAPI backend + Next.js (TypeScript) frontend

## 📋 Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose** (optional, for containerized deployment)
- **Ollama** (for local LLM) - [Install Ollama](https://ollama.ai)
- **Supabase Account** - [Create Account](https://supabase.com)
- **OpenAI API Key** (optional, for fallback) - [Get API Key](https://platform.openai.com)

## 🚀 Quick Start

### 1. Clone and Setup Environment

```bash
cd "f:\Mitigating AI Halucination\Modular code"

# Copy environment template
copy .env.example .env

# Edit .env with your actual credentials
notepad .env
```

### 2. Configure Environment Variables

Edit `.env` and set:

```env
# Required
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# Recommended
OPENAI_API_KEY=sk-your-openai-key  # For LLM fallback
JWT_SECRET_KEY=your-secure-random-key  # Generate with: openssl rand -hex 32

# Optional (defaults shown)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### 3. Setup Supabase Database

Run this SQL in your Supabase SQL Editor:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create documents table
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB,
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create vector similarity search function
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(768),
    match_threshold FLOAT,
    match_count INT
)
RETURNS TABLE (
    id BIGINT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE SQL STABLE
AS $$
    SELECT
        id,
        content,
        metadata,
        1 - (embedding <=> query_embedding) AS similarity
    FROM documents
    WHERE 1 - (embedding <=> query_embedding) > match_threshold
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$;

-- Create index for faster searches
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops);

-- Create profiles table for user roles
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id),
    email TEXT,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can read all documents"
    ON documents FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Admins can insert documents"
    ON documents FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );
```

### 4. Install Ollama and Pull Model

```bash
# Install Ollama from https://ollama.ai

# Pull the model
ollama pull llama3.1:8b

# Verify Ollama is running
curl http://localhost:11434/api/tags
```

## 🐳 Docker Deployment

### Production Stack

Prerequisites: copy `.env.example` to `.env` and fill in Supabase and other keys (Compose mounts this into the backend).

```bash
# Build and start backend + frontend
docker compose up --build -d

# View logs
docker compose logs -f

# Stop (named volumes such as the Hugging Face model cache are kept)
docker compose down

# Stop and remove the model cache volume
docker compose down -v
```

Services exposed by Compose:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

### Deployment Notes

- Set `DEBUG=False` in `.env` before deployment.
- Set `NEXT_PUBLIC_API_URL` and `CORS_ORIGINS` when the browser talks to a different host than `localhost` (for example your public API URL and site URL, comma-separated for CORS).
- Compose uses **one Uvicorn worker** by default so PyTorch and embedding models are not loaded twice in RAM. Scale vertically (more container memory) before adding workers.
- A named volume **`huggingface_cache`** stores downloaded Transformers / Sentence-Transformers weights so restarts are faster.
- **Ollama on the host**: `OLLAMA_BASE_URL` defaults to `http://host.docker.internal:11434`. Compose adds `extra_hosts` so Linux engines resolve `host.docker.internal`; Docker Desktop on Windows/macOS already provides it.
- `admin/ingest` may be intentionally disabled in read-only deployments. The UI and API now report that explicitly.

## 💻 Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📚 API Documentation

Once running, access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Key Endpoints

#### Authentication
- `POST /auth/signup` - Create new user account
- `POST /auth/login` - Login and get JWT token

#### Research/Chat
- `POST /chat/query` - Submit research query (requires auth)

#### Admin (requires admin role)
- `POST /admin/ingest` - Upload and index documents
- `GET /admin/stats` - Get knowledge base statistics

### Example Usage

```bash
# 1. Signup
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepass123"}'

# 2. Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepass123"}'

# 3. Query (use token from login)
curl -X POST http://localhost:8000/chat/query \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"What are the key principles of contract law?","scope":"HYBRID"}'
```

## 🏗️ Project Structure

```
├── app/
│   ├── main.py              # FastAPI app with Rate Limiting
│   ├── config.py            # Pydantic Settings & Config
│   ├── models.py            # Pydantic models (Auth, Chat, Admin)
│   ├── dependencies.py      # Security & Supabase dependencies
│   ├── routers/             # API endpoints (Rate Limited)
│   │   ├── auth.py          # Authentication (Signup, Login, Profile)
│   │   ├── chat.py          # Research Queries & History
│   │   └── admin.py         # Knowledge Base Management
│   ├── services/            # Business logic
│   │   ├── research.py      # Research Orchestration
│   │   ├── global_kb.py     # Knowledge Base Service
│   │   └── cache.py         # Result Caching Service
│   └── core/                # Core AI & Search Utilities
│       ├── ollama_utils.py  # LLM Client (Ollama + OpenAI)
│       ├── summarizer.py    # BART Grounded Summarization
│       ├── web_search.py    # Tavily & DuckDuckGo Tools
│       └── embedding_store.py # BGE Embedding Model Management
├── frontend/                # Next.js UI (standalone production Dockerfile)
├── legacy/                  # Legacy CLI tools and logs
├── tests/                   # Automated Pytest Suite
├── Dockerfile               # Backend API image
├── docker-compose.yml       # Backend + frontend stack
├── requirements.txt
├── pytest.ini               # Test configuration
└── .env.example
```

## 🔧 Configuration

### LLM Configuration

**Ollama (Primary)**:
- Runs locally for privacy and cost savings
- Configure via `OLLAMA_BASE_URL` and `OLLAMA_MODEL`
- In Docker, use `http://host.docker.internal:11434`

**OpenAI (Fallback)**:
- Automatically used if Ollama is unavailable
- Configure via `OPENAI_API_KEY` and `OPENAI_MODEL`
- Optional but recommended for reliability

### CORS Configuration

Add your frontend URLs to `CORS_ORIGINS` in `.env`:

```env
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,https://yourdomain.com
```

## 🐛 Troubleshooting

### Ollama Connection Issues

**Error**: `Ollama not available`

**Solutions**:
1. Verify Ollama is running: `curl http://localhost:11434/api/tags`
2. In Docker, ensure `OLLAMA_BASE_URL=http://host.docker.internal:11434`
3. Check firewall settings
4. Ensure OpenAI fallback is configured

### Supabase Connection Issues

**Error**: `Could not connect to Supabase`

**Solutions**:
1. Verify credentials in `.env`
2. Check Supabase project is active
3. Verify network connectivity
4. Check RLS policies allow your operations

### Docker Health Check Failing

**Error**: `Container unhealthy`

**Solutions**:
1. Check logs: `docker-compose logs web`
2. Verify port 8000 is not in use
3. Ensure all environment variables are set
4. Wait for startup period (40s)

### Import Errors

**Error**: `ModuleNotFoundError`

**Solutions**:
1. Rebuild Docker image: `docker-compose build --no-cache`
2. For local dev: `pip install -r requirements.txt`
3. Verify Python version is 3.11+

## 📊 Monitoring

### Health Checks

```bash
# Basic health
curl http://localhost:8000/health

# Detailed info
curl http://localhost:8000/api/info

# Docker health status
docker-compose ps
```

### Logs

```bash
# Docker logs
docker-compose logs -f web

# Local logs (configured in app/main.py)
# Logs to console with format: timestamp - name - level - message
```

## 🔐 Security Notes

- **JWT Secret**: Change `JWT_SECRET_KEY` in production
- **Service Role Key**: Keep `SUPABASE_SERVICE_ROLE_KEY` secret
- **CORS**: Restrict `CORS_ORIGINS` to your domains only
- **HTTPS**: Use HTTPS in production (configure reverse proxy)
- **RLS**: Supabase Row Level Security is enabled

## 🚦 Next Steps

1. **Frontend Integration**: Use the API with React, Vue, or Next.js
2. **Custom Models**: Add more Ollama models or fine-tuned models
3. **Monitoring**: Add Sentry, DataDog, or similar
4. **Caching**: Implement Redis for response caching
5. **Rate Limiting**: Add rate limiting middleware

## 📝 License

[Your License Here]

## 🤝 Contributing

[Your Contributing Guidelines Here]

## 📧 Support

For issues and questions:
- GitHub Issues: [Your Repo]
- Email: [Your Email]
- Documentation: http://localhost:8000/docs
