"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { Scale, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ChatInput } from "@/components/chat/chat-input";
import { ChatMessage, StreamingMessage } from "@/components/chat/chat-message";
import { SourcesList } from "@/components/chat/source-card";
import { ConversationSidebar } from "@/components/chat/conversation-sidebar";
import { useAuthStore } from "@/store/auth-store";
import { useChatStore } from "@/store/chat-store";
import { streamChatQuery } from "@/services/chat-service";
import { useQueryClient } from "@tanstack/react-query";
import type { Message, Source } from "@/types/api";

export default function ResearchPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAuthenticated, user, logout } = useAuthStore();
  const {
    currentConversationId,
    setCurrentConversation,
    messages,
    setMessages,
    addMessage,
    sources,
    setSources,
    isStreaming,
    setIsStreaming,
    streamingContent,
    setStreamingContent,
    appendStreamingContent,
    searchScope,
    resetChat,
  } = useChatStore();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, router]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  const handleSend = useCallback(
    (query: string) => {
      // Add user message
      const userMessage: Message = {
        id: `msg-${Date.now()}`,
        role: "user",
        content: query,
        created_at: new Date().toISOString(),
      };
      addMessage(userMessage);

      // Clear previous sources and start streaming
      setSources([]);
      setIsStreaming(true);
      setStreamingContent("");

      // Start streaming request
      abortControllerRef.current = streamChatQuery(
        {
          query,
          scope: searchScope,
          conversation_id: currentConversationId || undefined,
        },
        {
          onToken: (token) => {
            appendStreamingContent(token);
          },
          onSources: (newSources) => {
            setSources(newSources as Source[]);
          },
          onConversationId: (id) => {
            if (id !== currentConversationId) {
              setCurrentConversation(id);
              // Invalidate sidebar to show new conversation immediately
              queryClient.invalidateQueries({ queryKey: ["conversations"] });
            }
          },
          onError: (error) => {
            console.error("Chat error:", error);
            setIsStreaming(false);

            // Add error message
            const errorMessage: Message = {
              id: `msg-${Date.now()}`,
              role: "assistant",
              content: `Sorry, an error occurred: ${error.message}. Please try again.`,
              created_at: new Date().toISOString(),
            };
            addMessage(errorMessage);
          },
          onComplete: () => {
            const currentContent = useChatStore.getState().streamingContent;
            const currentSources = useChatStore.getState().sources;

            // Add assistant message
            const assistantMessage: Message = {
              id: `msg-${Date.now()}`,
              role: "assistant",
              content: currentContent,
              sources: currentSources,
              created_at: new Date().toISOString(),
            };
            addMessage(assistantMessage);
            setIsStreaming(false);
            setStreamingContent("");
          },
        }
      );
    },
    [
      addMessage,
      setSources,
      setIsStreaming,
      setStreamingContent,
      appendStreamingContent,
      searchScope,
      currentConversationId,
      setCurrentConversation,
    ]
  );

  const handleNewResearch = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    resetChat();
    setSidebarOpen(false);
  };

  const handleSelectConversation = (conversationId: string, conversationMessages: Message[]) => {
    setCurrentConversation(conversationId);
    setMessages(conversationMessages);
    setSources([]);
    setSidebarOpen(false);
  };

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-80 transform bg-sidebar border-r border-sidebar-border transition-transform lg:relative lg:translate-x-0 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"
          }`}
      >
        <div className="flex h-full flex-col">
          {/* Sidebar Header */}
          <div className="flex items-center justify-between border-b border-sidebar-border p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent">
                <Scale className="h-5 w-5 text-accent-foreground" />
              </div>
              <span className="font-semibold">Legal Research</span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* New Research Button */}
          <div className="p-4">
            <Button
              onClick={handleNewResearch}
              className="w-full"
              variant="outline"
            >
              New Research
            </Button>
          </div>

          {/* Conversations */}
          <ConversationSidebar
            onSelectConversation={handleSelectConversation}
            currentConversationId={currentConversationId}
          />

          {/* User Menu */}
          <div className="border-t border-sidebar-border p-4">
            <div className="flex items-center justify-between">
              <div className="truncate">
                <p className="text-sm font-medium truncate">{user?.email}</p>
                <p className="text-xs text-muted-foreground capitalize">
                  {user?.role}
                </p>
              </div>
              <Button variant="ghost" size="sm" onClick={handleLogout}>
                Logout
              </Button>
            </div>
            {user?.role === "admin" && (
              <Button
                variant="outline"
                size="sm"
                className="mt-3 w-full"
                onClick={() => router.push("/admin")}
              >
                Admin Panel
              </Button>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex flex-1 flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center gap-4 border-b border-border px-4 py-3 lg:px-6">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </Button>
          <h1 className="text-lg font-semibold">Research Assistant</h1>
        </header>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 lg:p-6">
          {(!messages || messages.length === 0) && !isStreaming ? (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-accent/10 mb-6">
                <Scale className="h-8 w-8 text-accent" />
              </div>
              <h2 className="text-2xl font-semibold mb-2">
                Legal Research Assistant
              </h2>
              <p className="text-muted-foreground max-w-md leading-relaxed">
                Ask any legal research question. I will search through trusted
                legal documents and provide answers with verifiable citations.
              </p>
            </div>
          ) : (
            <div className="mx-auto max-w-4xl space-y-6">
              {messages?.map((message) => (
                <ChatMessage key={message.id || `msg-${message.created_at}`} message={message} />
              ))}

              {/* Streaming Message */}
              {isStreaming && (
                <StreamingMessage content={streamingContent} />
              )}

              {/* Streaming Sources */}
              {isStreaming && sources.length > 0 && (
                <div className="pl-[52px]">
                  <SourcesList sources={sources} />
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-border bg-background p-4 lg:p-6">
          <div className="mx-auto max-w-4xl">
            <ChatInput onSend={handleSend} disabled={!isAuthenticated} />
          </div>
        </div>
      </main>
    </div>
  );
}
