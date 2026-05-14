import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { AlertCircle, CheckCircle2, KeyRound, Loader2, ShieldCheck } from "lucide-react";
import { acceptInvite } from "@/lib/auth";

export function AcceptInvitePage() {
  const location = useLocation();
  const navigate = useNavigate();
  const params = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const inviteSecret = params.get("invite_secret") ?? params.get("token") ?? "";
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");

  const acceptMut = useMutation({
    mutationFn: () =>
      acceptInvite({
        invite_secret: inviteSecret,
        password,
        full_name: fullName.trim() || undefined,
      }),
    onSuccess: () => navigate("/overview", { replace: true }),
  });

  const missingInvite = !inviteSecret;
  const validPassword =
    password.length >= 8 && /[A-Z]/.test(password) && /\d/.test(password);

  return (
    <main className="flex min-h-screen items-center justify-center bg-ink px-4 py-10 text-bone">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(229,177,110,0.16),transparent_34%),radial-gradient(circle_at_80%_20%,rgba(110,168,254,0.12),transparent_32%)]" />
      <section className="frame relative w-full max-w-lg p-6 shadow-2xl">
        <div className="mb-5 flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-brass/30 bg-brass/10 text-brass-2">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <div className="font-mono text-[11px] uppercase tracking-[0.15em] text-muted">
              Veklom workspace invite
            </div>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight">Join the workspace</h1>
            <p className="mt-1 text-sm text-bone-2">
              Accept this invite link to create or attach your account to the invited Veklom workspace.
            </p>
          </div>
        </div>

        {missingInvite ? (
          <div className="rounded-lg border border-crimson/40 bg-crimson/5 p-4 text-sm text-crimson">
            <div className="flex items-start gap-2">
              <AlertCircle className="mt-0.5 h-4 w-4" />
              <div>
                <div className="font-semibold">Invite link is missing</div>
                <div className="mt-1 text-xs opacity-80">
                  Ask the workspace admin to generate a fresh invite from the Team page.
                </div>
              </div>
            </div>
          </div>
        ) : (
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              if (validPassword) acceptMut.mutate();
            }}
          >
            <label className="block">
              <div className="v-label">Full name</div>
              <input
                className="v-input w-full"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Jane Smith"
                autoComplete="name"
              />
            </label>

            <label className="block">
              <div className="v-label">Password</div>
              <input
                className="v-input w-full"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="8+ chars, one uppercase, one number"
                autoComplete="new-password"
              />
            </label>

            <div className="grid gap-2 rounded-lg border border-rule bg-ink-1/70 p-3 font-mono text-[11px] text-muted">
              <div className="flex items-center gap-2">
                {password.length >= 8 ? <CheckCircle2 className="h-3.5 w-3.5 text-moss" /> : <KeyRound className="h-3.5 w-3.5" />}
                At least 8 characters
              </div>
              <div className="flex items-center gap-2">
                {/[A-Z]/.test(password) ? <CheckCircle2 className="h-3.5 w-3.5 text-moss" /> : <KeyRound className="h-3.5 w-3.5" />}
                One uppercase letter
              </div>
              <div className="flex items-center gap-2">
                {/\d/.test(password) ? <CheckCircle2 className="h-3.5 w-3.5 text-moss" /> : <KeyRound className="h-3.5 w-3.5" />}
                One number
              </div>
            </div>

            {acceptMut.isError && (
              <div className="rounded-lg border border-crimson/40 bg-crimson/5 p-3 text-[12px] text-crimson">
                {(acceptMut.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
                  (acceptMut.error as Error)?.message}
              </div>
            )}

            <button className="v-btn-primary w-full" disabled={!validPassword || acceptMut.isPending}>
              {acceptMut.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
              {acceptMut.isPending ? "Accepting invite..." : "Accept invite"}
            </button>
          </form>
        )}

        <div className="mt-5 border-t border-rule pt-4 text-center text-xs text-muted">
          Already have access?{" "}
          <Link className="text-brass-2 hover:underline" to="/login">
            Sign in
          </Link>
        </div>
      </section>
    </main>
  );
}
