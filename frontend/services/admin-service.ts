import { apiRequest, API_BASE_URL } from "./api-client";
import { useAuthStore } from "@/store/auth-store";
import type { AdminStats, IngestResponse } from "@/types/api";

export async function getAdminStats(): Promise<AdminStats> {
  return apiRequest<AdminStats>("/admin/stats");
}

export async function ingestDocument(file: File): Promise<IngestResponse> {
  const token = useAuthStore.getState().token;
  
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/admin/ingest`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    let detail = "Failed to ingest document";
    try {
      const errorData = await response.json();
      detail = errorData.detail || detail;
    } catch {
      // Ignore
    }
    throw new Error(detail);
  }

  return response.json();
}
