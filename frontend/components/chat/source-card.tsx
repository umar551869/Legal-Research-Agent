"use client";

import { ExternalLink, FileText, Globe, Database } from "lucide-react";
import type { Source } from "@/types/api";

interface SourceCardProps {
  source: Source;
  index: number;
}

export function SourceCard({ source, index }: SourceCardProps) {
  const similarityPercent = Math.round(source.similarity * 100);
  const isWeb = source.source_type === "web" || source.url.startsWith("http");

  const getHostname = (urlStr: string) => {
    try {
      return new URL(urlStr).hostname;
    } catch (e) {
      return "Web Source";
    }
  };
  
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex flex-col justify-between rounded-xl border border-border bg-card/50 p-4 transition-all hover:border-accent hover:bg-card hover:shadow-sm"
    >
      <div>
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-md bg-secondary text-xs font-semibold text-secondary-foreground">
              {index + 1}
            </span>
            {isWeb ? (
              <span className="flex items-center gap-1.5 rounded-full bg-blue-500/10 px-2 py-0.5 text-xs font-medium text-blue-400">
                <Globe className="h-3 w-3" />
                Web
              </span>
            ) : (
              <span className="flex items-center gap-1.5 rounded-full bg-purple-500/10 px-2 py-0.5 text-xs font-medium text-purple-400">
                <Database className="h-3 w-3" />
                Internal
              </span>
            )}
          </div>
          
          <div className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            similarityPercent >= 80
              ? "bg-accent/20 text-accent"
              : similarityPercent >= 60
              ? "bg-yellow-500/20 text-yellow-500"
              : "bg-muted text-muted-foreground"
          }`}>
            {similarityPercent}% Match
          </div>
        </div>
        
        <h4 className="mt-1 font-semibold text-foreground line-clamp-2 leading-tight group-hover:text-accent transition-colors">
          {source.title}
        </h4>
        
        <p className="mt-2 text-sm text-muted-foreground line-clamp-3 leading-relaxed">
          {source.snippet}
        </p>
      </div>
      
      <div className="mt-4 flex items-center justify-between border-t border-border/50 pt-3">
        <span className="text-xs text-muted-foreground truncate max-w-[80%]">
          {isWeb ? getHostname(source.url) : "Local Knowledge Base"}
        </span>
        <ExternalLink className="h-4 w-4 text-muted-foreground transition-colors group-hover:text-accent" />
      </div>
    </a>
  );
}

interface SourcesListProps {
  sources: Source[];
}

export function SourcesList({ sources }: SourcesListProps) {
  if (sources.length === 0) return null;
  
  return (
    <div className="space-y-3 my-4">
      <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
        <FileText className="h-4 w-4" />
        Consulted Sources ({sources.length})
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sources.map((source, index) => (
          <SourceCard key={`${source.url}-${index}`} source={source} index={index} />
        ))}
      </div>
    </div>
  );
}
