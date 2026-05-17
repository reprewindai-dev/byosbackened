import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { register } from "@/lib/auth";

export function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register({ email, password, full_name: fullName, workspace_name: workspaceName });
      navigate("/overview", { replace: true });
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err as Error)?.message ?? "Registration failed";
      setError(typeof detail === "string" ? detail : "Registration failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="relative grid min-h-screen place-items-center overflow-hidden bg-ink px-4">
      <div className="pointer-events-none absolute inset-0 opacity-[0.03]" style={{
        backgroundImage: "linear-gradient(rgba(229,177,110,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(229,177,110,0.3) 1px, transparent 1px)",
        backgroundSize: "60px 60px",
      }} />

      <div className="relative w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center">
          <svg viewBox="0 0 48 48" className="mb-4 h-14 w-14">
            <path d="M24 6 L10 38 L16 38 L24 20 L32 38 L38 38 Z" fill="#e5a832" />
            <circle cx="24" cy="30" r="3.5" fill="#e5a832" />
          </svg>
          <h1 className="text-2xl font-bold tracking-tight text-bone">Create Workspace</h1>
          <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.2em] text-muted">
            Deploy sovereign in minutes
          </p>
        </div>

        <form onSubmit={onSubmit} className="v-card space-y-4">
          <div>
            <label className="v-label" htmlFor="name">Full Name</label>
            <input id="name" type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} className="v-input" placeholder="Jane Doe" />
          </div>
          <div>
            <label className="v-label" htmlFor="ws">Workspace Name</label>
            <input id="ws" type="text" required value={workspaceName} onChange={(e) => setWorkspaceName(e.target.value)} className="v-input" placeholder="Acme Corp" />
          </div>
          <div>
            <label className="v-label" htmlFor="reg-email">Email</label>
            <input id="reg-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="v-input" placeholder="you@company.com" />
          </div>
          <div>
            <label className="v-label" htmlFor="reg-pass">Password</label>
            <input id="reg-pass" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="v-input" placeholder="Min 8 chars, 1 upper, 1 number" />
          </div>

          {error && (
            <div className="rounded-md border border-crimson/30 bg-crimson/8 px-3 py-2 text-xs text-crimson">
              {error}
            </div>
          )}

          <button type="submit" disabled={submitting} className="v-btn-primary w-full">
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {submitting ? "Creating..." : "Create workspace"}
          </button>

          <div className="pt-2 text-center font-mono text-[10px] text-muted">
            Already have a workspace?{" "}
            <Link to="/login" className="text-brass hover:text-brass-2 transition-colors">Sign in</Link>
          </div>
        </form>
      </div>
    </div>
  );
}
