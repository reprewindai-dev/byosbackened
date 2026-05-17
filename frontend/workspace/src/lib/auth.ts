import { api } from "./api";
import type { AcceptInviteRequest, AuthResponse, LoginRequest, RegisterRequest, User } from "@/types/api";
import { useAuthStore } from "@/store/auth-store";

export async function login(payload: LoginRequest): Promise<User> {
  const resp = await api.post<AuthResponse>("/auth/login", payload);
  return persistAuth(resp.data);
}

export async function register(payload: RegisterRequest): Promise<User> {
  const resp = await api.post<AuthResponse>("/auth/register", payload);
  return persistAuth(resp.data);
}

export async function acceptInvite(payload: AcceptInviteRequest): Promise<User> {
  const resp = await api.post<AuthResponse>("/auth/accept-invite", payload);
  persistAuth(resp.data);
  return fetchMe();
}

export async function logout(): Promise<void> {
  try {
    await api.post("/auth/logout", {});
  } catch {
    /* best-effort */
  }
  useAuthStore.getState().clear();
}

export async function fetchMe(): Promise<User> {
  const resp = await api.get<{ user: User } | User>("/auth/me");
  const user = "user" in (resp.data as { user?: User }) ? (resp.data as { user: User }).user : (resp.data as User);
  useAuthStore.getState().setUser(user);
  return user;
}

function persistAuth(payload: AuthResponse): User {
  const store = useAuthStore.getState();
  store.setTokens({
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token,
    expiresAt: Date.now() + payload.expires_in * 1000,
  });
  if (payload.user) store.setUser(payload.user);
  return payload.user ?? ({} as User);
}
