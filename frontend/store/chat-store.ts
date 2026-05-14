import { create } from "zustand";
import type { Message, Source, SearchScope, Conversation } from "@/types/api";

interface ChatState {
  currentConversationId: string | null;
  messages: Message[];
  sources: Source[];
  isStreaming: boolean;
  streamingContent: string;
  searchScope: SearchScope;
  conversations: Conversation[];
  
  setCurrentConversation: (id: string | null) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  setSources: (sources: Source[]) => void;
  setIsStreaming: (isStreaming: boolean) => void;
  setStreamingContent: (content: string) => void;
  appendStreamingContent: (chunk: string) => void;
  setSearchScope: (scope: SearchScope) => void;
  setConversations: (conversations: Conversation[]) => void;
  resetChat: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  currentConversationId: null,
  messages: [],
  sources: [],
  isStreaming: false,
  streamingContent: "",
  searchScope: "HYBRID",
  conversations: [],

  setCurrentConversation: (id) => set({ currentConversationId: id }),
  setMessages: (messages) => set({ messages: Array.isArray(messages) ? messages : [] }),
  addMessage: (message) =>
    set((state) => ({
      messages: [...(Array.isArray(state.messages) ? state.messages : []), message],
    })),
  setSources: (sources) => set({ sources }),
  setIsStreaming: (isStreaming) => set({ isStreaming }),
  setStreamingContent: (content) => set({ streamingContent: content }),
  appendStreamingContent: (chunk) =>
    set((state) => ({ streamingContent: state.streamingContent + chunk })),
  setSearchScope: (scope) => set({ searchScope: scope }),
  setConversations: (conversations) =>
    set({ conversations: Array.isArray(conversations) ? conversations : [] }),
  resetChat: () =>
    set({
      currentConversationId: null,
      messages: [],
      sources: [],
      isStreaming: false,
      streamingContent: "",
    }),
}));
