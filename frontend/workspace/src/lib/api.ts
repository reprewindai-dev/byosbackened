import axios, { type AxiosInstance } from "axios";
import { useAuthStore } from "@/store/auth-store";

declare global {
  interface Window {
    __VEKLOM_API_BASE__?: string;
  }
}

const API_PREFIX = "/api/v1";

function resolveBase(): string {
  const configured = window.__VEKLOM_API_BASE__;
  if (configured) return `${configured}${API_PREFIX}`;
  // Dev mode — point to Vite dev server so proxy works even from external preview
  if (import.meta.env.DEV) return `http://localhost:5173${API_PREFIX}`;
  return API_PREFIX;
}

export const api: AxiosInstance = axios.create({
  baseURL: resolveBase(),
  headers: { "Content-Type": "application/json" },
});

// Attach bearer token to every request
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 → attempt refresh (skip for auth endpoints)
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const url = original?.url || "";
    const isAuthEndpoint = url.includes("/auth/login") || url.includes("/auth/register") || url.includes("/auth/refresh");

    if (error.response?.status === 401 && !original._retry && !isAuthEndpoint) {
      original._retry = true;
      const refreshToken = useAuthStore.getState().refreshToken;
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${resolveBase()}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          useAuthStore.getState().setTokens(data.access_token, data.refresh_token, data.expires_in);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return api(original);
        } catch {
          useAuthStore.getState().logout();
        }
      }
    }
    return Promise.reject(error);
  },
);

export function sseUrl(path: string): string {
  const token = useAuthStore.getState().accessToken;
  const base = `${resolveBase()}${path}`;
  return token ? `${base}${base.includes("?") ? "&" : "?"}token=${token}` : base;
}
