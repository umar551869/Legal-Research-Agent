import { useAuthStore } from "@/store/auth-store";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

async function getAuthHeaders(): Promise<HeadersInit> {
  const token = useAuthStore.getState().token;
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return headers;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = await getAuthHeaders();

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      ...headers,
      ...options.headers,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      useAuthStore.getState().logout();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }

    let detail = "An error occurred";
    try {
      const errorData = await response.json();
      detail = errorData.detail || detail;
    } catch {
      // Ignore JSON parse errors
    }

    throw new ApiError(response.status, detail);
  }

  // Handle empty responses
  const text = await response.text();
  if (!text) {
    return {} as T;
  }

  return JSON.parse(text);
}

export function createStreamingRequest(
  endpoint: string,
  body: unknown,
  onChunk: (chunk: string) => void,
  onSources?: (sources: unknown[]) => void,
  onConversationId?: (id: string) => void,
  onError?: (error: Error) => void,
  onComplete?: () => void
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const headers = await getAuthHeaders();

      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!response.ok) {
        if (response.status === 401) {
          useAuthStore.getState().logout();
          window.location.href = "/login";
          return;
        }

        let detail = "An error occurred";
        try {
          const errorData = await response.json();
          detail = errorData.detail || detail;
        } catch {
          // Ignore
        }
        throw new ApiError(response.status, detail);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No response body");
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          onComplete?.();
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);

            if (data === "[DONE]") {
              onComplete?.();
              return;
            }

            try {
              const parsed = JSON.parse(data);

              if (parsed.error && onError) {
                onError(new Error(parsed.error));
                return;
              }

              if (parsed.sources && onSources) {
                onSources(parsed.sources);
              }

              if (parsed.conversation_id && onConversationId) {
                onConversationId(parsed.conversation_id);
              }

              if (parsed.token) {
                onChunk(parsed.token);
              } else if (parsed.content) {
                onChunk(parsed.content);
              } else if (typeof parsed === "string") {
                onChunk(parsed);
              }
            } catch {
              // If not JSON, treat as plain text token
              // REMOVED .trim() to preserve whitespace (spaces, newlines)
              if (data) {
                onChunk(data);
              }
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        return;
      }
      onError?.(error as Error);
    }
  })();

  return controller;
}

export { API_BASE_URL };
