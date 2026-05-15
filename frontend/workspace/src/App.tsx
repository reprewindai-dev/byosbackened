import { useEffect } from "react";
import { AppRoutes } from "./routes";
import { useAuthStore } from "./store/auth-store";
import { fetchMe } from "./lib/auth";
import { useProductTelemetry } from "./lib/product-telemetry";
import { SupportBotWidget } from "./components/SupportBotWidget";

export default function App() {
  const hydrate = useAuthStore((s) => s.hydrate);
  const status = useAuthStore((s) => s.status);
  useProductTelemetry();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (status === "authenticated") {
      void fetchMe().catch(() => undefined);
    }
  }, [status]);

  return (
    <>
      <AppRoutes />
      {status === "authenticated" && <SupportBotWidget />}
    </>
  );
}
