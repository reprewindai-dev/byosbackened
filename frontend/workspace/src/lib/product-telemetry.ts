import { useEffect, useMemo, useRef } from "react";
import { useLocation } from "react-router-dom";
import { api } from "./api";
import { useAuthStore } from "@/store/auth-store";

const STORAGE_KEY = "veklom.telemetry.session.v1";

function sessionId(): string {
  if (typeof window === "undefined") return "";
  const existing = window.localStorage.getItem(STORAGE_KEY);
  if (existing) return existing;
  const value = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  window.localStorage.setItem(STORAGE_KEY, value);
  return value;
}

function surfaceFromPath(pathname: string): string {
  const clean = pathname.replace(/^\/+/, "").split("/")[0] || "home";
  return clean === "control-center" || clean === "dashboard" ? "sunnyvale" : clean;
}

export function useProductTelemetry() {
  const location = useLocation();
  const status = useAuthStore((s) => s.status);
  const accessToken = useAuthStore((s) => s.accessToken);
  const sid = useMemo(sessionId, []);
  const enteredAt = useRef(Date.now());
  const lastPath = useRef(location.pathname);

  useEffect(() => {
    if (status !== "authenticated" || !accessToken) return;
    const route = location.pathname;
    lastPath.current = route;
    enteredAt.current = Date.now();
    void api.post("/telemetry/events", {
      events: [
        {
          event_type: "page_view",
          session_id: sid,
          route,
          surface: surfaceFromPath(route),
          metadata: {
            referrer: document.referrer || null,
            viewport: `${window.innerWidth}x${window.innerHeight}`,
            tab_visible: document.visibilityState === "visible",
          },
        },
      ],
    }).catch(() => undefined);
  }, [accessToken, location.pathname, sid, status]);

  useEffect(() => {
    if (status !== "authenticated" || !accessToken) return;

    const sendActiveTime = () => {
      const now = Date.now();
      const duration = Math.max(0, now - enteredAt.current);
      enteredAt.current = now;
      if (duration < 1000) return;
      void api.post("/telemetry/events", {
        events: [
          {
            event_type: "active_time",
            session_id: sid,
            route: lastPath.current,
            surface: surfaceFromPath(lastPath.current),
            duration_ms: Math.min(duration, 5 * 60 * 1000),
            metadata: { tab_visible: document.visibilityState === "visible" },
          },
        ],
      }).catch(() => undefined);
    };

    const interval = window.setInterval(sendActiveTime, 30_000);
    window.addEventListener("visibilitychange", sendActiveTime);
    window.addEventListener("pagehide", sendActiveTime);
    return () => {
      sendActiveTime();
      window.clearInterval(interval);
      window.removeEventListener("visibilitychange", sendActiveTime);
      window.removeEventListener("pagehide", sendActiveTime);
    };
  }, [accessToken, sid, status]);
}
