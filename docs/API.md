# API Documentation

## Base URL

- **Local Development**: `http://localhost:8000`
- **Docker**: `http://localhost:8000`
- **Production**: `https://your-domain.com`

## Authentication

All protected endpoints require a JWT token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

---

## Endpoints

### Authentication

#### POST /auth/signup

Create a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (201):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer"
}
```

**Errors:**
- `400`: Email already exists or invalid data
- `201`: Email confirmation required (check email)

---

#### POST /auth/login

Login with existing credentials.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer"
}
```

**Errors:**
- `400`: Invalid credentials

---

### Research / Chat

#### POST /chat/query

Submit a research query as an SSE stream. **Requires authentication.**

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "What are the key principles of contract law?",
  "scope": "HYBRID"
}
```

**Scope Options:**
- `INTERNAL_DB`: Search only internal knowledge base
- `EXTERNAL_WEB`: Search only external web sources
- `HYBRID`: Search both internal and external (recommended)
- `UPLOADED_DOC`: Search uploaded documents (if applicable)

**Response (200):**
`text/event-stream`

The stream sends:
- First event: `{"sources":[...],"conversation_id":"...","intent":"RESEARCH"}`
- Token events: `{"token":"..."}`
- Final event: `[DONE]`

**Errors:**
- `401`: Unauthorized (invalid or missing token)
- `500`: Internal server error

**Example cURL:**
```bash
curl -X POST http://localhost:8000/chat/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key principles of contract law?",
    "scope": "HYBRID"
  }'
```

---

### Admin Endpoints

**Note:** These endpoints require the user to have `role='admin'` in the profiles table.

#### POST /admin/ingest

Upload and index a document into the knowledge base.
Some deployments run in read-only mode and return `503` when ingestion is disabled.

**Headers:**
```
Authorization: Bearer <admin_token>
Content-Type: multipart/form-data
```

**Request Body (Form Data):**
- `file`: Text file to upload (.txt, .md, etc.)

**Response (200):**
```json
{
  "filename": "legal_document.txt",
  "status": "success",
  "chunks_processed": 42
}
```

**Errors:**
- `401`: Unauthorized
- `403`: Forbidden (not an admin)
- `400`: Invalid file or processing error
- `500`: Internal server error
- `503`: Ingestion disabled for this deployment

**Example cURL:**
```bash
curl -X POST http://localhost:8000/admin/ingest \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -F "file=@/path/to/document.txt"
```

---

#### GET /admin/stats

Get knowledge base statistics.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Response (200):**
```json
{
  "total_vectors": 1234
}
```

**Errors:**
- `401`: Unauthorized
- `403`: Forbidden (not an admin)

---

### System Endpoints

#### GET /

Root endpoint with API information.

**Response (200):**
```json
{
  "message": "Welcome to Legal Research AI API",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/health"
}
```

---

#### GET /health

Health check endpoint for monitoring.

**Response (200):**
```json
{
  "status": "healthy",
  "service": "Legal Research AI API",
  "version": "1.0.0"
}
```

---

#### GET /info

API configuration information.

**Response (200):**
```json
{
  "app_name": "Legal Research AI API",
  "version": "1.0.0",
  "debug_mode": false,
  "ollama_url": "http://localhost:11434",
  "ollama_model": "llama3.1:8b",
  "openai_enabled": true
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message or error details"
}
```

### Common HTTP Status Codes

- `200`: Success
- `201`: Created
- `400`: Bad Request (validation error)
- `401`: Unauthorized (missing or invalid token)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found
- `422`: Unprocessable Entity (validation error with details)
- `500`: Internal Server Error

---

## Rate Limiting

Currently not implemented. Consider adding rate limiting for production use.

---

## Interactive Documentation

For interactive API testing, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These provide:
- Interactive request/response testing
- Automatic request validation
- Schema documentation
- Authentication testing

---

## Authentication Flow

### 1. Create Account

```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepass123"}'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepass123"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer"
}
```

### 3. Use Token

```bash
curl -X POST http://localhost:8000/chat/query \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{"query":"Your question here","scope":"HYBRID"}'
```

---

## Frontend Integration Examples

### JavaScript (Fetch API)

```javascript
// Login
const loginResponse = await fetch('http://localhost:8000/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'securepass123'
  })
});
const { access_token } = await loginResponse.json();

// Query
const queryResponse = await fetch('http://localhost:8000/chat/query', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: 'What are the key principles of contract law?',
    scope: 'HYBRID'
  })
});
const result = await queryResponse.json();
console.log(result.answer);
```

### Python (requests)

```python
import requests

# Login
login_response = requests.post(
    'http://localhost:8000/auth/login',
    json={'email': 'user@example.com', 'password': 'securepass123'}
)
token = login_response.json()['access_token']

# Query
query_response = requests.post(
    'http://localhost:8000/chat/query',
    headers={'Authorization': f'Bearer {token}'},
    json={'query': 'What are the key principles of contract law?', 'scope': 'HYBRID'}
)
result = query_response.json()
print(result['answer'])
```

---

## WebSocket Support

Not currently implemented. Consider adding for real-time streaming responses.
