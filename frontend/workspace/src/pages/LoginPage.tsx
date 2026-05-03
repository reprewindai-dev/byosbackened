import { FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { ShieldCheck, Loader2 } from "lucide-react";
import { login } from "@/lib/auth";
import { useAuthStore } from "@/store/auth-store";

export function LoginPage() {
  const status = useAuthStore((s) => s.status);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const from = (location.state as { from?: string } | null)?.from ?? "/overview";

  if (status === "authenticated") return <Navigate to={from} replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login({ email, password });
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        "Login failed";
      setError(typeof detail === "string" ? detail : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brass/15">
            <ShieldCheck className="h-5 w-5 text-brass-2" />
          </div>
          <h1 className="text-xl font-semibold tracking-tight">Sign in to Veklom</h1>
          <p className="font-mono text-[11px] uppercase tracking-[0.1em] text-muted">Sovereign Control Node</p>
        </div>

        <form onSubmit={onSubmit} className="v-card p-6">
          <div className="mb-4">
            <label className="v-label" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="v-input"
              placeholder="you@acme.io"
            />
          </div>
          <div className="mb-4">
            <label className="v-label" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="v-input"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div className="mb-4 rounded-md border border-crimson/30 bg-crimson/10 px-3 py-2 text-[12px] text-crimson">
              {error}
            </div>
          )}

          <button type="submit" disabled={submitting} className="v-btn-primary w-full">
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {submitting ? "Signing in…" : "Sign in"}
          </button>

          <div className="mt-4 flex items-center justify-between font-mono text-[11px] text-muted">
            <a href="/signup/" className="hover:text-bone">Create workspace</a>
            <a href="/auth/reset" className="hover:text-bone">Forgot password</a>
          </div>
        </form>

        <div className="mt-4 text-center font-mono text-[10px] uppercase tracking-[0.15em] text-muted">
          mTLS internal · SOC2-ready · EU-sovereign
        </div>
      </div>
    </div>
  );
}
