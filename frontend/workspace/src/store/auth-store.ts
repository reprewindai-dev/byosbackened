import { create } from "zustand";

export interface User {
  id: string;
  email: string;
  full_name?: string;
  role: string;
  workspace_id: string;
  workspace_name?: string;
  workspace_slug?: string;
  industry?: string;
  mfa_enabled?: boolean;
  is_superuser?: boolean;
  github_username?: string;
  github_connected?: boolean;
  license_tier?: string;
  license_expires_at?: string;
}

interface AuthState {
  status: "idle" | "authenticated" | "unauthenticated";
  accessToken: string | null;
  refreshToken: string | null;
  expiresAt: number | null;
  user: User | null;

  setTokens: (access: string, refresh: string, expiresIn: number) => void;
  setUser: (user: User) => void;
  logout: () => void;
  hydrate: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  status: "idle",
  accessToken: null,
  refreshToken: null,
  expiresAt: null,
  user: null,

  setTokens: (access, refresh, expiresIn) => {
    const expiresAt = Date.now() + expiresIn * 1000;
    localStorage.setItem("vk_at", access);
    localStorage.setItem("vk_rt", refresh);
    localStorage.setItem("vk_exp", String(expiresAt));
    set({ accessToken: access, refreshToken: refresh, expiresAt, status: "authenticated" });
  },

  setUser: (user) => {
    localStorage.setItem("vk_user", JSON.stringify(user));
    set({ user });
  },

  logout: () => {
    localStorage.removeItem("vk_at");
    localStorage.removeItem("vk_rt");
    localStorage.removeItem("vk_exp");
    localStorage.removeItem("vk_user");
    set({ accessToken: null, refreshToken: null, expiresAt: null, user: null, status: "unauthenticated" });
  },

  hydrate: () => {
    const at = localStorage.getItem("vk_at");
    const rt = localStorage.getItem("vk_rt");
    const exp = localStorage.getItem("vk_exp");
    const userJson = localStorage.getItem("vk_user");

    if (at && rt && exp && Number(exp) > Date.now()) {
      const user = userJson ? JSON.parse(userJson) : null;
      set({ accessToken: at, refreshToken: rt, expiresAt: Number(exp), user, status: "authenticated" });
    } else {
      set({ status: "unauthenticated" });
    }
  },
}));
