// Authentication Types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
}

// Signup may return this instead of AuthResponse when email confirmation is needed
export interface SignupConfirmationResponse {
  detail: string;
  requires_confirmation: boolean;
}

export interface User {
  id: string;
  email: string;
  role: "user" | "admin";
}

// Chat Types
export type SearchScope = "HYBRID" | "INTERNAL_DB" | "EXTERNAL_WEB";

export interface ChatQueryRequest {
  query: string;
  scope: SearchScope;
  conversation_id?: string;
}

export interface Source {
  title: string;
  snippet: string;
  similarity: number;
  url: string;
  source_type?: "web" | "internal"; // injected by frontend based on URL
}

export interface Message {
  id?: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  created_at?: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count?: number;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

// Admin Types — matches backend AdminStatsResponse
export interface AdminStats {
  total_vectors: number | string;
  ingestion_enabled: boolean;
}

// Matches backend DocumentUploadResponse
export interface IngestResponse {
  filename: string;
  status: string;
  chunks_processed: number;
}

// API Error
export interface ApiError {
  detail: string;
  status_code: number;
}
