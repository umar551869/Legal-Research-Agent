import { apiRequest } from "./api-client";
import type { AuthResponse, LoginRequest, SignupRequest, User, SignupConfirmationResponse } from "@/types/api";

export async function login(credentials: LoginRequest): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export async function signup(data: SignupRequest): Promise<AuthResponse | SignupConfirmationResponse> {
  return apiRequest<AuthResponse | SignupConfirmationResponse>("/auth/signup", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getCurrentUser(): Promise<User> {
  return apiRequest<User>("/auth/me");
}

export async function logout(): Promise<void> {
  try {
    await apiRequest("/auth/logout", { method: "POST" });
  } catch {
    // Ignore logout errors, we clear local state anyway
  }
}
