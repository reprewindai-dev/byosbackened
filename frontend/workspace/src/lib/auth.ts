import { api } from "./api";
import { useAuthStore, type User } from "@/store/auth-store";

interface LoginPayload {
  email: string;
  password: string;
  mfa_code?: string;
}

interface RegisterPayload {
  email: string;
  password: string;
  full_name?: string;
  workspace_name?: string;
  signup_type?: string;
}

interface AuthResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user_id: string;
  workspace_id: string;
  role: string;
}

export async function login(payload: LoginPayload): Promise<User | null> {
  const { data } = await api.post<AuthResponse>("/auth/login", payload);
  useAuthStore.getState().setTokens(data.access_token, data.refresh_token, data.expires_in);
  return fetchMe();
}

export async function register(payload: RegisterPayload): Promise<User | null> {
  const { data } = await api.post<AuthResponse>("/auth/register", payload);
  useAuthStore.getState().setTokens(data.access_token, data.refresh_token, data.expires_in);
  return fetchMe();
}

export async function fetchMe(): Promise<User | null> {
  try {
    const { data } = await api.get<User>("/auth/me");
    useAuthStore.getState().setUser(data);
    return data;
  } catch {
    return null;
  }
}

export async function logout(): Promise<void> {
  try {
    await api.post("/auth/logout");
  } catch {
    // ignore
  }
  useAuthStore.getState().logout();
}

export async function beginGithubLogin(): Promise<{ auth_url: string }> {
  const { data } = await api.get<{ auth_url: string }>("/auth/github/login");
  return data;
}
