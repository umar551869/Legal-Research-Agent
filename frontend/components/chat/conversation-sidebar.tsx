"use client";

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { MessageSquare, Loader2, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useChatStore } from "@/store/chat-store";
import { getConversations, getConversation, deleteConversation } from "@/services/chat-service";
import type { Message, Conversation } from "@/types/api";

interface ConversationSidebarProps {
  onSelectConversation: (id: string, messages: Message[]) => void;
  currentConversationId: string | null;
}

export function ConversationSidebar({
  onSelectConversation,
  currentConversationId,
}: ConversationSidebarProps) {
  const { conversations, setConversations } = useChatStore();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["conversations"],
    queryFn: getConversations,
    staleTime: 30000,
  });

  useEffect(() => {
    if (data) {
      setConversations(data);
    }
  }, [data, setConversations]);

  const handleSelectConversation = async (conversation: Conversation) => {
    try {
      const detail = await getConversation(conversation.id);
      onSelectConversation(conversation.id, Array.isArray(detail.messages) ? detail.messages : []);
    } catch (error) {
      console.error("Failed to load conversation:", error);
    }
  };

  const handleDeleteConversation = async (
    e: React.MouseEvent,
    conversationId: string
  ) => {
    e.stopPropagation();
    
    try {
      await deleteConversation(conversationId);
      refetch();
    } catch (error) {
      console.error("Failed to delete conversation:", error);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) {
      return "Unknown";
    }
    const date = new Date(dateString);
    const now = new Date();
    const diffDays = Math.floor(
      (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24)
    );

    if (diffDays === 0) {
      return "Today";
    } else if (diffDays === 1) {
      return "Yesterday";
    } else if (diffDays < 7) {
      return `${diffDays} days ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  return (
    <div className="flex-1 overflow-hidden">
      <div className="px-4 py-2">
        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Recent Conversations
        </h3>
      </div>

      <ScrollArea className="h-[calc(100%-2rem)]">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : !Array.isArray(conversations) || conversations.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <MessageSquare className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">No conversations yet</p>
            <p className="text-xs text-muted-foreground mt-1">
              Start a new research to begin
            </p>
          </div>
        ) : (
          <div className="px-2 pb-4 space-y-1">
            {conversations.map((conversation) => (
              <div
                key={conversation.id}
                onClick={() => handleSelectConversation(conversation)}
                className={`group w-full flex items-start justify-between gap-2 rounded-lg px-3 py-2.5 text-left transition-colors cursor-pointer ${
                  currentConversationId === conversation.id
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "hover:bg-sidebar-accent/50"
                }`}
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">
                    {conversation.title || "Untitled Research"}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {formatDate(conversation.updated_at)} · {conversation.message_count} messages
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                  onClick={(e) => handleDeleteConversation(e, conversation.id)}
                >
                  <Trash2 className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
