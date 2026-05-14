import { apiRequest, createStreamingRequest } from "./api-client";
import type {
  ChatQueryRequest,
  Conversation,
  ConversationDetail,
  Source,
} from "@/types/api";

export async function getConversations(): Promise<Conversation[]> {
  return apiRequest<Conversation[]>("/chat/conversations");
}

export async function getConversation(id: string): Promise<ConversationDetail> {
  return apiRequest<ConversationDetail>(`/chat/conversation/${id}`);
}

export async function deleteConversation(id: string): Promise<void> {
  return apiRequest<void>(`/chat/conversation/${id}`, {
    method: "DELETE",
  });
}

export function streamChatQuery(
  request: ChatQueryRequest,
  callbacks: {
    onToken: (token: string) => void;
    onSources: (sources: Source[]) => void;
    onConversationId?: (id: string) => void;
    onError: (error: Error) => void;
    onComplete: () => void;
  }
): AbortController {
  return createStreamingRequest(
    "/chat/query",
    request,
    callbacks.onToken,
    callbacks.onSources as (sources: unknown[]) => void,
    callbacks.onConversationId,
    callbacks.onError,
    callbacks.onComplete
  );
}
