import { create } from "zustand";
import type { User } from "@/types/api";

const STORAGE_KEY = "veklom.auth.v1";

interface Tokens {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  expiresAt: number | null;
  user: User | null;
  status: "idle" | "authenticated" | "unauthenticated";
  hydrate: () => void;
  setTokens: (t: Tokens) => void;
  setUser: (u: User | null) => void;
  clear: () => void;
}

function readPersisted(): Partial<AuthState> | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function persist(state: Partial<AuthState>) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        expiresAt: state.expiresAt,
        user: state.user,
      }),
    );
  } catch {
    /* ignore quota errors */
  }
}

function clearPersisted() {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  refreshToken: null,
  expiresAt: null,
  user: null,
  status: "idle",

  hydrate: () => {
    const saved = readPersisted();
    if (saved?.accessToken && saved?.refreshToken) {
      set({
        accessToken: saved.accessToken,
        refreshToken: saved.refreshToken,
        expiresAt: saved.expiresAt ?? null,
        user: saved.user ?? null,
        status: "authenticated",
      });
    } else {
      set({ status: "unauthenticated" });
    }
  },

  setTokens: ({ accessToken, refreshToken, expiresAt }) => {
    set({ accessToken, refreshToken, expiresAt, status: "authenticated" });
    persist({ ...get(), accessToken, refreshToken, expiresAt });
  },

  setUser: (user) => {
    set({ user });
    persist({ ...get(), user });
  },

  clear: () => {
    set({
      accessToken: null,
      refreshToken: null,
      expiresAt: null,
      user: null,
      status: "unauthenticated",
    });
    clearPersisted();
  },
}));
