import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Loader2, ShieldCheck } from "lucide-react";

import { completeGithubCallback, completeGithubMfa } from "@/lib/auth";

export function GithubCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mfaRequired, setMfaRequired] = useState(false);
  const [challengeToken, setChallengeToken] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const code = searchParams.get("code") || "";
    const state = searchParams.get("state") || "";
    if (!code || !state) {
      setLoading(false);
      setError("Missing GitHub OAuth callback parameters.");
      return;
    }
    (async () => {
      try {
        const payload = await completeGithubCallback(code, state);
        if (payload.mfa_required && payload.mfa_challenge_token) {
          setMfaRequired(true);
          setChallengeToken(payload.mfa_challenge_token);
          setLoading(false);
          return;
        }
        navigate("/", { replace: true });
      } catch (err: unknown) {
        const detail =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          (err as Error)?.message ??
          "GitHub sign-in failed";
        setError(typeof detail === "string" ? detail : "GitHub sign-in failed");
        setLoading(false);
      }
    })();
  }, [navigate, searchParams]);

  async function onSubmitMfa(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await completeGithubMfa(challengeToken, mfaCode);
      navigate("/", { replace: true });
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (err as Error)?.message ??
        "GitHub MFA verification failed";
      setError(typeof detail === "string" ? detail : "GitHub MFA verification failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brass/15">
            <ShieldCheck className="h-5 w-5 text-brass-2" />
          </div>
          <h1 className="text-xl font-semibold tracking-tight">GitHub workspace connection</h1>
          <p className="font-mono text-[11px] uppercase tracking-[0.1em] text-muted">OAuth callback</p>
        </div>
        <div className="v-card p-6">
          {loading && (
            <div className="flex items-center justify-center gap-2 text-sm text-bone-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Completing GitHub sign-in...
            </div>
          )}
          {!loading && mfaRequired && (
            <form onSubmit={onSubmitMfa}>
              <div className="mb-4 text-sm text-bone-2">
                This GitHub-connected account requires MFA before access is granted.
              </div>
              <label className="block">
                <div className="v-label">MFA or backup code</div>
                <input
                  className="v-input w-full"
                  autoComplete="one-time-code"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value.replace(/\s+/g, "").toUpperCase())}
                  placeholder="123456 or backup code"
                />
              </label>
              {error && (
                <div className="mt-4 rounded-md border border-crimson/30 bg-crimson/10 px-3 py-2 text-[12px] text-crimson">
                  {error}
                </div>
              )}
              <button type="submit" disabled={submitting || !mfaCode} className="v-btn-primary mt-4 w-full">
                {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                {submitting ? "Verifying..." : "Verify MFA and continue"}
              </button>
            </form>
          )}
          {!loading && !mfaRequired && error && (
            <div className="rounded-md border border-crimson/30 bg-crimson/10 px-3 py-2 text-[12px] text-crimson">
              {error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
