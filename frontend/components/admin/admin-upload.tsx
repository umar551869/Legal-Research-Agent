"use client";

import { useState, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Upload, File, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { getAdminStats, ingestDocument } from "@/services/admin-service";

interface UploadStatus {
  file: File;
  status: "pending" | "uploading" | "success" | "error";
  progress: number;
  message?: string;
  chunksProcessed?: number;
}

export function AdminUpload() {
  const [uploads, setUploads] = useState<UploadStatus[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { data: stats } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: getAdminStats,
    staleTime: 30000,
  });
  const ingestionEnabled = Boolean(stats?.ingestion_enabled);

  const handleFileSelect = async (files: FileList | null) => {
    if (!files || !ingestionEnabled) return;

    const validFiles = Array.from(files).filter((file) => {
      const extension = file.name.toLowerCase().split(".").pop();
      return extension === "pdf" || extension === "txt";
    });

    if (validFiles.length === 0) {
      return;
    }

    const newUploads: UploadStatus[] = validFiles.map((file) => ({
      file,
      status: "pending",
      progress: 0,
    }));

    setUploads((prev) => [...prev, ...newUploads]);

    // Process uploads one by one
    for (const upload of newUploads) {
      await processUpload(upload);
    }
  };

  const processUpload = async (upload: UploadStatus) => {
    setUploads((prev) =>
      prev.map((u) =>
        u.file === upload.file
          ? { ...u, status: "uploading", progress: 10 }
          : u
      )
    );

    // Simulate progress
    const progressInterval = setInterval(() => {
      setUploads((prev) =>
        prev.map((u) =>
          u.file === upload.file && u.status === "uploading"
            ? { ...u, progress: Math.min(u.progress + 10, 90) }
            : u
        )
      );
    }, 200);

    try {
      const response = await ingestDocument(upload.file);

      clearInterval(progressInterval);

      setUploads((prev) =>
        prev.map((u) =>
          u.file === upload.file
            ? {
                ...u,
                status: "success",
                progress: 100,
                message: `Uploaded ${response.filename}`,
                chunksProcessed: response.chunks_processed,
              }
            : u
        )
      );
    } catch (error) {
      clearInterval(progressInterval);

      setUploads((prev) =>
        prev.map((u) =>
          u.file === upload.file
            ? {
                ...u,
                status: "error",
                progress: 0,
                message:
                  error instanceof Error ? error.message : "Upload failed",
              }
            : u
        )
      );
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const clearCompleted = () => {
    setUploads((prev) =>
      prev.filter((u) => u.status !== "success" && u.status !== "error")
    );
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="space-y-6">
      {/* Upload Area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative rounded-xl border-2 border-dashed p-12 text-center transition-colors ${
          !ingestionEnabled
            ? "border-border/50 bg-muted/30 opacity-60"
            : isDragging
            ? "border-accent bg-accent/5"
            : "border-border hover:border-muted-foreground/50"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt"
          multiple
          onChange={(e) => handleFileSelect(e.target.files)}
          disabled={!ingestionEnabled}
          className="absolute inset-0 cursor-pointer opacity-0"
        />
        
        <div className="flex flex-col items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
            <Upload className="h-8 w-8 text-muted-foreground" />
          </div>
          <div>
            <p className="text-lg font-medium">
              {ingestionEnabled ? "Drop files here or click to upload" : "Document ingestion is disabled"}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {ingestionEnabled ? "Supports PDF and TXT files" : "This deployment is running in read-only mode"}
            </p>
          </div>
          <Button
            variant="outline"
            disabled={!ingestionEnabled}
            onClick={() => inputRef.current?.click()}
          >
            Select Files
          </Button>
        </div>
      </div>

      {/* Upload List */}
      {uploads.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">Uploads</h3>
            <Button variant="ghost" size="sm" onClick={clearCompleted}>
              Clear completed
            </Button>
          </div>

          <div className="space-y-2">
            {uploads.map((upload, index) => (
              <div
                key={`${upload.file.name}-${index}`}
                className="flex items-center gap-4 rounded-lg border border-border bg-card p-4"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                  <File className="h-5 w-5 text-muted-foreground" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium truncate">{upload.file.name}</p>
                    <span className="text-xs text-muted-foreground shrink-0">
                      {formatFileSize(upload.file.size)}
                    </span>
                  </div>

                  {upload.status === "uploading" && (
                    <Progress value={upload.progress} className="mt-2 h-1.5" />
                  )}

                  {upload.message && (
                    <p
                      className={`mt-1 text-sm ${
                        upload.status === "error"
                          ? "text-destructive"
                          : "text-muted-foreground"
                      }`}
                    >
                      {upload.message}
                      {upload.chunksProcessed !== undefined && (
                        <span className="ml-2">
                          ({upload.chunksProcessed} chunks processed)
                        </span>
                      )}
                    </p>
                  )}
                </div>

                <div className="shrink-0">
                  {upload.status === "uploading" && (
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                  )}
                  {upload.status === "success" && (
                    <CheckCircle2 className="h-5 w-5 text-accent" />
                  )}
                  {upload.status === "error" && (
                    <XCircle className="h-5 w-5 text-destructive" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
