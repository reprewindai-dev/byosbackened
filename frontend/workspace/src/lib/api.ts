import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "@/store/auth-store";

declare global {
  interface Window {
    __VEKLOM_API_BASE__?: string;
    __VEKLOM_ENV__?: string;
    __VEKLOM_STRIPE_PK__?: string;
  }
}

export function resolveApiBase(): string {
  if (typeof window !== "undefined" && window.__VEKLOM_API_BASE__) {
    return window.__VEKLOM_API_BASE__.replace(/\/+$/, "");
  }
  const buildTime = import.meta.env.VITE_VEKLOM_API_BASE as string | undefined;
  if (buildTime) return buildTime.replace(/\/+$/, "");
  if (typeof location !== "undefined") {
    const h = location.hostname;
    if (/^localhost$|^127\.|^0\.0\.0\.0$/.test(h)) return "";
    if (/veklom\.dev$/i.test(h)) return "https://api.veklom.dev";
    if (/veklom\.com$/i.test(h)) return "https://api.veklom.com";
  }
  return "";
}

export function resolveStripePk(): string {
  if (typeof window !== "undefined" && window.__VEKLOM_STRIPE_PK__) return window.__VEKLOM_STRIPE_PK__;
  return (import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY as string | undefined) ?? "";
}

const API_BASE = resolveApiBase();
const API_PREFIX = "/api/v1";
const DEFAULT_API_TIMEOUT_MS = 25_000;
const AUTH_API_TIMEOUT_MS = 20_000;

export const api: AxiosInstance = axios.create({
  baseURL: `${API_BASE}${API_PREFIX}`,
  timeout: DEFAULT_API_TIMEOUT_MS,
  withCredentials: false,
  transitional: { clarifyTimeoutError: true },
});

export const apiRoot: AxiosInstance = axios.create({
  baseURL: API_BASE || "/",
  timeout: DEFAULT_API_TIMEOUT_MS,
  transitional: { clarifyTimeoutError: true },
});

function attachAuthHeader(config: InternalAxiosRequestConfig): InternalAxiosRequestConfig {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers = config.headers ?? {};
    (config.headers as Record<string, string>).Authorization = `Bearer ${token}`;
  }
  return config;
}

api.interceptors.request.use(attachAuthHeader);
apiRoot.interceptors.request.use(attachAuthHeader);

let refreshInFlight: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight;
  const { refreshToken, setTokens, clear } = useAuthStore.getState();
  if (!refreshToken) {
    clear();
    return null;
  }
  refreshInFlight = (async () => {
    try {
      const resp = await axios.post(
        `${API_BASE}${API_PREFIX}/auth/refresh`,
        { refresh_token: refreshToken },
        { timeout: AUTH_API_TIMEOUT_MS, transitional: { clarifyTimeoutError: true } },
      );
      const { access_token, refresh_token, expires_in } = resp.data as {
        access_token: string;
        refresh_token?: string;
        expires_in: number;
      };
      setTokens({
        accessToken: access_token,
        refreshToken: refresh_token ?? refreshToken,
        expiresAt: Date.now() + expires_in * 1000,
      });
      return access_token;
    } catch {
      clear();
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

function makeResponseInterceptor(instance: AxiosInstance) {
  instance.interceptors.response.use(
    (r) => r,
    async (error: AxiosError) => {
      const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean; _networkRetried?: boolean }) | undefined;
      const method = original?.method?.toLowerCase() ?? "get";
      const safeToRetry = method === "get" || method === "head" || method === "options";
      const transientTransportFailure =
        error.code === "ERR_NETWORK" ||
        error.code === "ECONNABORTED" ||
        error.code === "ETIMEDOUT" ||
        /network error|timeout/i.test(error.message);

      if (original && safeToRetry && transientTransportFailure && !original._networkRetried) {
        original._networkRetried = true;
        return instance.request(original);
      }

      if (error.response?.status === 401 && original && !original._retried) {
        original._retried = true;
        const fresh = await refreshAccessToken();
        if (fresh) {
          original.headers = original.headers ?? {};
          (original.headers as Record<string, string>).Authorization = `Bearer ${fresh}`;
          return instance.request(original);
        }
        if (typeof window !== "undefined" && window.location.pathname !== "/login") {
          window.location.href = "/login";
        }
      }
      return Promise.reject(error);
    },
  );
}

makeResponseInterceptor(api);
makeResponseInterceptor(apiRoot);

export function sseUrl(path: string, params?: Record<string, string | number | boolean>): string {
  const url = new URL(`${API_BASE}${API_PREFIX}${path}`, typeof window !== "undefined" ? window.location.origin : "http://localhost");
  if (params) {
    for (const [k, v] of Object.entries(params)) url.searchParams.set(k, String(v));
  }
  const token = useAuthStore.getState().accessToken;
  if (token) url.searchParams.set("access_token", token);
  return url.toString();
}
