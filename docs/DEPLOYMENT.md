# Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Supabase Setup](#supabase-setup)
3. [Local Development](#local-development)
4. [Docker Deployment](#docker-deployment)
5. [Production Deployment](#production-deployment)
6. [Monitoring & Logging](#monitoring--logging)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Services

1. **Supabase Account**
   - Sign up at [supabase.com](https://supabase.com)
   - Create a new project
   - Note your project URL and API keys

2. **Ollama** (for local LLM)
   - Install from [ollama.ai](https://ollama.ai)
   - Pull required model: `ollama pull llama3.1:8b`
   - Verify: `curl http://localhost:11434/api/tags`

3. **OpenAI API Key** (optional, for fallback)
   - Get from [platform.openai.com](https://platform.openai.com)
   - Recommended for production reliability

### System Requirements

- **Python**: 3.11 or higher
- **Docker**: 20.10+ (if using containers)
- **Docker Compose**: 2.0+ (if using containers)
- **RAM**: 8GB minimum (16GB recommended for Ollama)
- **Disk**: 10GB free space

---

## Supabase Setup

### 1. Create Database Schema

In your Supabase SQL Editor, run:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create documents table for vector storage
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

-- Create index for faster vector searches
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create profiles table for user roles
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can read all documents
CREATE POLICY "Users can read all documents"
    ON documents FOR SELECT
    TO authenticated
    USING (true);

-- RLS Policy: Only admins can insert documents
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

-- RLS Policy: Users can read their own profile
CREATE POLICY "Users can read own profile"
    ON profiles FOR SELECT
    TO authenticated
    USING (auth.uid() = id);

-- Trigger to create profile on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, role)
    VALUES (NEW.id, NEW.email, 'user');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

### 2. Get API Credentials

1. Go to **Project Settings** > **API**
2. Copy:
   - **Project URL** (e.g., `https://xxxxx.supabase.co`)
   - **anon/public key** (for `SUPABASE_KEY`)
   - **service_role key** (optional, for `SUPABASE_SERVICE_ROLE_KEY`)

### 3. Create Admin User

After creating your first user via the API, promote them to admin:

```sql
-- Replace with your user's email
UPDATE profiles
SET role = 'admin'
WHERE email = 'your-email@example.com';
```

---

## Local Development

### 1. Setup Environment

```bash
cd "f:\Mitigating AI Halucination\Modular code"

# Copy environment template
copy .env.example .env

# Edit with your credentials
notepad .env
```

### 2. Configure .env

```env
# Supabase
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OPENAI_API_KEY=sk-your-openai-key

# Security
JWT_SECRET_KEY=your-secure-random-key  # Generate: openssl rand -hex 32

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Verify

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

---

## Docker Deployment

### Compose Deployment

```bash
# Build and start backend + frontend
docker compose up --build -d

# View logs
docker compose logs -f backend frontend

# Stop
docker compose down
```

### Production Mode

1. **Update `.env` for production**:

```env
DEBUG=False
LOG_LEVEL=WARNING
JWT_SECRET_KEY=<strong-random-key>
CORS_ORIGINS=https://yourdomain.com
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

2. **Deploy**:

```bash
docker compose up -d --build
```

### Docker with Ollama Container (Optional)

If you want Ollama in Docker (requires GPU):

1. Uncomment Ollama service in `docker-compose.yml`
2. Update web service environment:

```yaml
environment:
  OLLAMA_BASE_URL: http://ollama:11434
```

3. Deploy:

```bash
docker-compose up -d --build
```

---

## Production Deployment

### Option 1: Cloud VM (AWS, GCP, Azure)

1. **Provision VM**:
   - Ubuntu 22.04 LTS
   - 4+ vCPUs, 16GB+ RAM
   - 50GB+ disk

2. **Install Docker**:

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

3. **Clone & Configure**:

```bash
git clone <your-repo>
cd <your-repo>
cp .env.example .env
nano .env  # Configure for production
```

4. **Deploy**:

```bash
docker-compose up -d --build
```

5. **Setup Reverse Proxy** (Nginx):

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

6. **Enable HTTPS** (Let's Encrypt):

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
```

### Option 2: Platform as a Service

#### Railway / Render / Fly.io

1. Connect GitHub repository
2. Set environment variables in dashboard
3. Deploy from main branch
4. Configure custom domain

**Note**: Ollama requires significant resources. Consider using OpenAI-only mode for PaaS deployments.

---

## Monitoring & Logging

### Health Checks

```bash
# Basic health
curl https://api.yourdomain.com/health

# Detailed info
curl https://api.yourdomain.com/api/info

# Docker health
docker-compose ps
```

### Logs

```bash
# Docker logs
docker-compose logs -f web

# Last 100 lines
docker-compose logs --tail=100 web

# Logs for specific time
docker-compose logs --since 2024-01-01T00:00:00 web
```

### Recommended Monitoring Tools

- **Uptime**: UptimeRobot, Pingdom
- **Errors**: Sentry
- **Metrics**: DataDog, New Relic
- **Logs**: Papertrail, Loggly

---

## Troubleshooting

### Ollama Not Available

**Symptom**: API falls back to OpenAI

**Solutions**:
1. Check Ollama is running: `curl http://localhost:11434/api/tags`
2. In Docker, verify `OLLAMA_BASE_URL=http://host.docker.internal:11434`
3. Check firewall allows port 11434
4. Verify model is pulled: `ollama list`

### Supabase Connection Failed

**Symptom**: 500 errors on auth/query endpoints

**Solutions**:
1. Verify credentials in `.env`
2. Check Supabase project is active
3. Verify RLS policies are correct
4. Check network connectivity

### Docker Container Unhealthy

**Symptom**: Container shows "unhealthy" status

**Solutions**:
1. Check logs: `docker-compose logs web`
2. Verify all env vars are set
3. Wait for startup period (40s)
4. Check port 8000 is not in use: `netstat -ano | findstr :8000`

### CORS Errors

**Symptom**: Frontend can't connect

**Solutions**:
1. Add frontend URL to `CORS_ORIGINS` in `.env`
2. Restart backend: `docker-compose restart web`
3. Verify frontend is using correct API URL
4. Check browser console for exact error

### High Memory Usage

**Symptom**: System running out of memory

**Solutions**:
1. Reduce Ollama model size (use smaller model)
2. Reduce worker count in production command
3. Increase VM memory
4. Use OpenAI-only mode (disable Ollama)

---

## Security Checklist

- [ ] Change `JWT_SECRET_KEY` to strong random value
- [ ] Keep `SUPABASE_SERVICE_ROLE_KEY` secret
- [ ] Restrict `CORS_ORIGINS` to your domains only
- [ ] Enable HTTPS in production
- [ ] Verify Supabase RLS policies
- [ ] Regular security updates: `docker-compose pull && docker-compose up -d`
- [ ] Monitor logs for suspicious activity
- [ ] Implement rate limiting
- [ ] Regular backups of Supabase data

---

## Backup & Recovery

### Supabase Backup

Supabase provides automatic backups. To export:

```bash
# Install Supabase CLI
npm install -g supabase

# Login
supabase login

# Export database
supabase db dump -f backup.sql
```

### Restore

```bash
supabase db reset
psql -h db.your-project.supabase.co -U postgres -f backup.sql
```

---

## Scaling

### Vertical Scaling

- Increase VM resources (CPU, RAM)
- Use larger Ollama models
- Increase worker count

### Horizontal Scaling

- Load balancer (Nginx, HAProxy)
- Multiple backend instances
- Shared Supabase database
- Redis for session/cache sharing

---

## Support

For deployment issues:
- Check logs first
- Review this guide
- Check GitHub issues
- Contact support
