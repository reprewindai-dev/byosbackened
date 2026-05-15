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

export async function beginGithubLogin(): Promise<{ auth_url: string; state: string }> {
  const resp = await api.get<{ auth_url: string; state: string }>("/auth/github");
  return resp.data;
}

export async function completeGithubCallback(code: string, state: string): Promise<AuthResponse> {
  const resp = await api.post<AuthResponse>("/auth/github/callback", { code, state });
  const payload = resp.data;
  if (payload.access_token && payload.refresh_token && payload.expires_in) {
    persistAuth(payload);
  }
  return payload;
}

export async function completeGithubMfa(challengeToken: string, mfaCode: string): Promise<User> {
  const resp = await api.post<AuthResponse>("/auth/github/mfa/complete", {
    challenge_token: challengeToken,
    mfa_code: mfaCode,
  });
  return persistAuth(resp.data);
}

function persistAuth(payload: AuthResponse): User {
  const store = useAuthStore.getState();
  if (!payload.access_token || !payload.refresh_token || !payload.expires_in) {
    return payload.user ?? ({} as User);
  }
  store.setTokens({
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token,
    expiresAt: Date.now() + payload.expires_in * 1000,
  });
  if (payload.user) store.setUser(payload.user);
  return payload.user ?? ({} as User);
}
