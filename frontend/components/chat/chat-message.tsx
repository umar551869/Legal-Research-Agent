"use client";

import { User, Bot } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import type { Message } from "@/types/api";
import { SourcesList } from "./source-card";

interface ChatMessageProps {
  message: Message;
}

const markdownComponents = {
  p: ({ children }: any) => (
    <p className="mb-4 last:mb-0 leading-7 text-[inherit]">{children}</p>
  ),
  ul: ({ children }: any) => (
    <ul className="mb-3 ml-4 list-disc space-y-1.5 [&>li]:pl-1">{children}</ul>
  ),
  ol: ({ children }: any) => (
    <ol className="mb-3 ml-4 list-decimal space-y-1.5 [&>li]:pl-1">{children}</ol>
  ),
  li: ({ children }: any) => (
    <li className="leading-7 text-[inherit]">{children}</li>
  ),
  strong: ({ children }: any) => (
    <strong className="font-bold text-white">{children}</strong>
  ),
  em: ({ children }: any) => (
    <em className="italic text-[inherit]">{children}</em>
  ),
  code: ({ children, className }: any) => {
    const isBlock = className?.includes("language-");
    if (isBlock) {
      return (
        <code className={`${className} text-sm`}>{children}</code>
      );
    }
    return (
      <code className="rounded bg-white/10 px-1.5 py-0.5 text-sm font-mono text-green-300">
        {children}
      </code>
    );
  },
  pre: ({ children }: any) => (
    <pre className="rounded-lg bg-black/40 border border-white/10 p-4 overflow-x-auto my-3 text-sm">
      {children}
    </pre>
  ),
  a: ({ href, children }: any) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-green-400 hover:text-green-300 underline underline-offset-2"
    >
      {children}
    </a>
  ),
  blockquote: ({ children }: any) => (
    <blockquote className="border-l-3 border-green-500/50 pl-4 italic text-gray-300 my-3">
      {children}
    </blockquote>
  ),
  h1: ({ children }: any) => (
    <h1 className="text-xl font-bold mt-5 mb-3 text-white border-b border-white/10 pb-2">{children}</h1>
  ),
  h2: ({ children }: any) => (
    <h2 className="text-lg font-bold mt-4 mb-2 text-white">{children}</h2>
  ),
  h3: ({ children }: any) => (
    <h3 className="text-base font-semibold mt-3 mb-1.5 text-white">{children}</h3>
  ),
  h4: ({ children }: any) => (
    <h4 className="text-sm font-semibold mt-2 mb-1 text-white">{children}</h4>
  ),
  hr: () => (
    <hr className="my-4 border-white/10" />
  ),
  table: ({ children }: any) => (
    <div className="overflow-x-auto my-3">
      <table className="min-w-full border-collapse border border-white/20 text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }: any) => (
    <thead className="bg-white/5">{children}</thead>
  ),
  th: ({ children }: any) => (
    <th className="border border-white/20 px-3 py-2 text-left font-semibold text-white">{children}</th>
  ),
  td: ({ children }: any) => (
    <td className="border border-white/20 px-3 py-2 text-[inherit]">{children}</td>
  ),
};

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-4 ${isUser ? "flex-row-reverse" : ""}`}>
      {/* Avatar */}
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
          isUser ? "bg-primary text-primary-foreground" : "bg-accent text-accent-foreground"
        }`}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Message Content */}
      <div className={`flex-1 space-y-3 ${isUser ? "text-right" : ""}`}>
        <div
          className={`inline-block max-w-[85%] rounded-xl px-5 py-4 ${
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-card border border-border text-foreground"
          }`}
        >
          {isUser ? (
            <p className="leading-relaxed">{message.content}</p>
          ) : (
            <div className="max-w-none text-gray-200">
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkBreaks]}
                components={markdownComponents}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Sources (for assistant messages) */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="max-w-[85%]">
            <SourcesList sources={message.sources} />
          </div>
        )}
      </div>
    </div>
  );
}

interface StreamingMessageProps {
  content: string;
}

export function StreamingMessage({ content }: StreamingMessageProps) {
  return (
    <div className="flex gap-4">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
        <Bot className="h-4 w-4" />
      </div>
      <div className="flex-1">
        <div className="inline-block max-w-[85%] rounded-xl px-5 py-4 bg-card border border-border text-foreground">
          <div className="max-w-none text-gray-200">
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkBreaks]}
              components={markdownComponents}
            >
              {content || "Thinking..."}
            </ReactMarkdown>
            <span className="inline-block w-2 h-4 ml-0.5 bg-accent animate-pulse rounded-sm" />
          </div>
        </div>
      </div>
    </div>
  );
}
