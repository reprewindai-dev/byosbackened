import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { login, beginGithubLogin } from "@/lib/auth";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [mfaRequired, setMfaRequired] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user = await login({ email, password, mfa_code: mfaCode || undefined });
      navigate(user?.is_superuser ? "/overview" : "/overview", { replace: true });
    } catch (err: unknown) {
      const axErr = err as { response?: { status?: number; data?: { detail?: string } }; message?: string; code?: string };
      const detail = axErr.response?.data?.detail;
      const status = axErr.response?.status;
      const code = axErr.code;
      let message: string;
      if (detail && typeof detail === "string") {
        message = detail;
      } else if (status) {
        message = `Server returned ${status}`;
      } else if (code === "ERR_NETWORK") {
        message = "Network error — backend may be unreachable";
      } else {
        message = axErr.message || "Login failed";
      }
      if (message.toLowerCase().includes("mfa")) setMfaRequired(true);
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  async function onGithub() {
    try {
      const { auth_url } = await beginGithubLogin();
      window.location.href = auth_url;
    } catch {
      setError("GitHub sign-in unavailable");
    }
  }

  return (
    <div className="relative grid min-h-screen place-items-center overflow-hidden bg-ink px-4">
      {/* Background grid effect */}
      <div className="pointer-events-none absolute inset-0 opacity-[0.03]" style={{
        backgroundImage: "linear-gradient(rgba(229,177,110,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(229,177,110,0.3) 1px, transparent 1px)",
        backgroundSize: "60px 60px",
      }} />

      <div className="relative w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center">
          <svg viewBox="0 0 48 48" className="mb-4 h-14 w-14">
            <path d="M24 6 L10 38 L16 38 L24 20 L32 38 L38 38 Z" fill="#e5a832" />
            <circle cx="24" cy="30" r="3.5" fill="#e5a832" />
          </svg>
          <h1 className="text-2xl font-bold tracking-tight text-bone">Veklom</h1>
          <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.2em] text-muted">
            Sovereign Control Plane
          </p>
        </div>

        {/* Card */}
        <form onSubmit={onSubmit} className="v-card space-y-4">
          <div>
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
          <div>
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

          {mfaRequired && (
            <div>
              <label className="v-label" htmlFor="mfa">MFA Code</label>
              <input
                id="mfa"
                type="text"
                autoComplete="one-time-code"
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value.replace(/\s/g, ""))}
                className="v-input"
                placeholder="123456"
              />
            </div>
          )}

          {error && (
            <div className="rounded-md border border-crimson/30 bg-crimson/8 px-3 py-2 text-xs text-crimson">
              {error}
            </div>
          )}

          <button type="submit" disabled={submitting} className="v-btn-primary w-full">
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {submitting ? "Signing in..." : "Sign in"}
          </button>

          <button type="button" onClick={onGithub} className="v-btn-ghost w-full">
            Continue with GitHub
          </button>

          <div className="flex items-center justify-between pt-2 font-mono text-[10px] text-muted">
            <Link to="/register" className="hover:text-bone transition-colors">Create workspace</Link>
            <span className="cursor-pointer hover:text-bone transition-colors">Forgot password</span>
          </div>
        </form>

        <p className="mt-6 text-center font-mono text-[9px] uppercase tracking-[0.18em] text-muted-2">
          Governed AI execution · Policy enforced · Evidence ready
        </p>
      </div>
    </div>
  );
}
