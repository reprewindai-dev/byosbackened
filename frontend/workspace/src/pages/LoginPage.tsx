import { FormEvent, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ShieldCheck, Loader2, LogOut } from "lucide-react";

import { beginGithubLogin, login, logout } from "@/lib/auth";
import { useAuthStore } from "@/store/auth-store";

export function LoginPage() {
  const status = useAuthStore((s) => s.status);
  const currentUser = useAuthStore((s) => s.user);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [mfaRequired, setMfaRequired] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [githubSubmitting, setGithubSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const from =
    (location.state as { from?: string } | null)?.from ??
    (currentUser?.is_superuser ? "/control-center" : "/");

  if (status === "authenticated") {
    return (
      <div className="grid min-h-screen place-items-center px-4">
        <div className="w-full max-w-sm">
          <div className="mb-6 flex flex-col items-center gap-2 text-center">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brass/15">
              <ShieldCheck className="h-5 w-5 text-brass-2" />
            </div>
            <h1 className="text-xl font-semibold tracking-tight">You're already signed in</h1>
            <p className="font-mono text-[11px] uppercase tracking-[0.1em] text-muted">
              {currentUser?.email ?? currentUser?.full_name ?? "current session"}
            </p>
          </div>
          <div className="v-card p-6">
            <button
              type="button"
              className="v-btn-primary mb-3 w-full"
              onClick={() => navigate(from, { replace: true })}
            >
              Continue to {from}
            </button>
            <button
              type="button"
              className="v-btn-ghost w-full justify-center text-crimson hover:text-crimson"
              onClick={async () => {
                await logout();
              }}
            >
              <LogOut className="h-4 w-4" /> Sign out and use a different account
            </button>
            <div className="mt-4 text-center">
              <Link to="/register" className="font-mono text-[11px] text-muted hover:text-bone">
                Create a new workspace instead
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user = await login({ email, password, mfa_code: mfaCode || undefined });
      navigate(user?.is_superuser ? "/control-center" : from, { replace: true });
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        "Login failed";
      const message = typeof detail === "string" ? detail : "Login failed";
      if (message === "MFA code required" || message === "Invalid MFA code") {
        setMfaRequired(true);
      }
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  async function onGithubLogin() {
    setError(null);
    setGithubSubmitting(true);
    try {
      const payload = await beginGithubLogin();
      window.location.href = payload.auth_url;
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        "GitHub sign-in unavailable";
      setError(typeof detail === "string" ? detail : "GitHub sign-in unavailable");
    } finally {
      setGithubSubmitting(false);
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
              placeholder="you@company.com"
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
              placeholder="Password"
            />
          </div>
          {mfaRequired && (
            <div className="mb-4">
              <label className="v-label" htmlFor="mfa-code">MFA or backup code</label>
              <input
                id="mfa-code"
                type="text"
                autoComplete="one-time-code"
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value.replace(/\s+/g, "").toUpperCase())}
                className="v-input"
                placeholder="123456 or backup code"
              />
              <div className="mt-1 text-[11px] text-muted">
                Enter your authenticator code or an unused backup code.
              </div>
            </div>
          )}

          {error && (
            <div className="mb-4 rounded-md border border-crimson/30 bg-crimson/10 px-3 py-2 text-[12px] text-crimson">
              {error}
            </div>
          )}

          <button type="submit" disabled={submitting} className="v-btn-primary w-full">
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {submitting ? "Signing in..." : mfaRequired ? "Verify and sign in" : "Sign in"}
          </button>

          <button type="button" disabled={githubSubmitting} className="v-btn-ghost mt-3 w-full justify-center" onClick={onGithubLogin}>
            {githubSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {githubSubmitting ? "Redirecting to GitHub..." : "Continue with GitHub"}
          </button>

          <div className="mt-4 flex items-center justify-between font-mono text-[11px] text-muted">
            <Link to="/register" className="hover:text-bone">Create workspace</Link>
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
