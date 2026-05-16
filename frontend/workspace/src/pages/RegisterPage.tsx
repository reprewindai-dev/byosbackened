import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { Loader2, ShieldCheck } from "lucide-react";
import { beginGithubLogin, register } from "@/lib/auth";
import { useAuthStore } from "@/store/auth-store";

export function RegisterPage() {
  const status = useAuthStore((s) => s.status);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");
  const [industry, setIndustry] = useState("generic");
  const [submitting, setSubmitting] = useState(false);
  const [githubSubmitting, setGithubSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  // If already authenticated, redirect to login so the user gets the
  // explicit escape hatch (continue / sign out & switch).
  if (status === "authenticated") return <Navigate to="/login" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const params = new URLSearchParams(window.location.search);
      await register({
        email,
        password,
        full_name: name || undefined,
        workspace_name: workspaceName || undefined,
        signup_type: "workspace_register",
        industry,
        utm_source: params.get("utm_source") || undefined,
        utm_campaign: params.get("utm_campaign") || undefined,
      });
      navigate("/overview", { replace: true });
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        "Registration failed";
      setError(typeof detail === "string" ? detail : "Registration failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function onGithubSignup() {
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
          <h1 className="text-xl font-semibold tracking-tight">Create a Veklom workspace</h1>
          <p className="font-mono text-[11px] uppercase tracking-[0.1em] text-muted">
            Sovereign Control Node
          </p>
        </div>

        <form onSubmit={onSubmit} className="v-card p-6">
          <div className="mb-4">
            <label className="v-label" htmlFor="reg-name">Your name</label>
            <input
              id="reg-name"
              type="text"
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="v-input"
              placeholder="Jane Operator"
            />
          </div>
          <div className="mb-4">
            <label className="v-label" htmlFor="reg-workspace">Workspace name</label>
            <input
              id="reg-workspace"
              type="text"
              value={workspaceName}
              onChange={(e) => setWorkspaceName(e.target.value)}
              className="v-input"
              placeholder="Acme Production"
            />
          </div>
          <div className="mb-4">
            <label className="v-label" htmlFor="reg-industry">What kind of team are you?</label>
            <select
              id="reg-industry"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              className="v-input"
            >
              <option value="banking_fintech">Bank / fintech</option>
              <option value="healthcare_hospital">Hospital / healthcare</option>
              <option value="insurance">Insurance</option>
              <option value="legal_compliance">Legal / compliance</option>
              <option value="government_public_sector">Government / public sector</option>
              <option value="enterprise_operations">Enterprise operations</option>
              <option value="generic">Other</option>
            </select>
          </div>
          <div className="mb-4">
            <label className="v-label" htmlFor="reg-email">Work email</label>
            <input
              id="reg-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="v-input"
              placeholder="you@company.com"
            />
          </div>
          <div className="mb-4">
            <label className="v-label" htmlFor="reg-password">Password</label>
            <input
              id="reg-password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="v-input"
              placeholder="At least 8 characters"
            />
          </div>

          {error && (
            <div className="mb-4 rounded-md border border-crimson/30 bg-crimson/10 px-3 py-2 text-[12px] text-crimson">
              {error}
            </div>
          )}

          <button type="submit" disabled={submitting} className="v-btn-primary w-full">
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {submitting ? "Creating workspace…" : "Create workspace"}
          </button>

          <button type="button" disabled={githubSubmitting} className="v-btn-ghost mt-3 w-full justify-center" onClick={onGithubSignup}>
            {githubSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {githubSubmitting ? "Redirecting to GitHub…" : "Continue with GitHub"}
          </button>

          <div className="mt-4 text-center font-mono text-[11px] text-muted">
            Already have a workspace?{" "}
            <Link to="/login" className="hover:text-bone">Sign in</Link>
          </div>
        </form>

        <div className="mt-4 text-center font-mono text-[10px] uppercase tracking-[0.15em] text-muted">
          mTLS internal · SOC2-ready · EU-sovereign
        </div>
      </div>
    </div>
  );
}
