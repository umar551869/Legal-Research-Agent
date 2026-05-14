from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any

# --- Auth Models ---
class UserSignup(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserProfile(BaseModel):
    id: str
    email: str
    role: str = "user"
    token: Optional[str] = None

class AuthMeResponse(BaseModel):
    id: str
    email: str
    role: str

# --- Chat/Research Models ---
class ChatRequest(BaseModel):
    query: str
    scope: Optional[str] = "HYBRID"
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []
    conversation_id: str

class MessageBase(BaseModel):
    id: Optional[str] = None
    role: str
    content: str
    sources: Optional[List[Any]] = None
    created_at: Optional[str] = None

class ConversationBase(BaseModel):
    id: str
    title: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    message_count: Optional[int] = None

class ConversationDetail(ConversationBase):
    messages: List[MessageBase] = []
    
# --- Admin Models ---
class DocumentUploadResponse(BaseModel):
    filename: str
    status: str
    chunks_processed: int

class AdminStatsResponse(BaseModel):
    total_vectors: int | str = 0
    ingestion_enabled: bool = False
