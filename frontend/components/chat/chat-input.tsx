"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2, Database, Globe, Shuffle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useChatStore } from "@/store/chat-store";
import type { SearchScope } from "@/types/api";

interface ChatInputProps {
  onSend: (query: string) => void;
  disabled?: boolean;
}

const scopeOptions: { value: SearchScope; label: string; icon: React.ReactNode; description: string }[] = [
  {
    value: "HYBRID",
    label: "Hybrid",
    icon: <Shuffle className="h-4 w-4" />,
    description: "Search both internal documents and web",
  },
  {
    value: "INTERNAL_DB",
    label: "Internal",
    icon: <Database className="h-4 w-4" />,
    description: "Search internal legal documents only",
  },
  {
    value: "EXTERNAL_WEB",
    label: "Web",
    icon: <Globe className="h-4 w-4" />,
    description: "Search external web sources",
  },
];

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [query, setQuery] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { searchScope, setSearchScope, isStreaming } = useChatStore();

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [query]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !disabled && !isStreaming) {
      onSend(query.trim());
      setQuery("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {/* Search Scope Selector */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Search scope:</span>
        <div className="flex gap-1">
          {scopeOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setSearchScope(option.value)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md transition-colors ${
                searchScope === option.value
                  ? "bg-accent text-accent-foreground"
                  : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
              }`}
              title={option.description}
            >
              {option.icon}
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Input Area */}
      <div className="relative flex items-end gap-2 rounded-xl border border-border bg-card p-3">
        <textarea
          ref={textareaRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a legal research question..."
          disabled={disabled || isStreaming}
          rows={1}
          className="flex-1 resize-none bg-transparent text-foreground placeholder:text-muted-foreground focus:outline-none min-h-[24px] max-h-[200px] leading-relaxed"
        />
        <Button
          type="submit"
          size="icon"
          disabled={!query.trim() || disabled || isStreaming}
          className="shrink-0 h-10 w-10"
        >
          {isStreaming ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Send className="h-5 w-5" />
          )}
        </Button>
      </div>
    </form>
  );
}
