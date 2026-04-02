"use client";

import { useMemo, useState } from "react";

type RunResponse = {
  ok: boolean;
  provider: string;
  output: any;
  raw?: any;
  error?: string;
};

export default function Page() {
  const [appId, setAppId] = useState("lead-radar");
  const [task, setTask] = useState("score_and_draft");
  const [input, setInput] = useState("Paste content here...");
  const [metaUrl, setMetaUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [resp, setResp] = useState<RunResponse | null>(null);

  const payload = useMemo(() => ({
    appId,
    task,
    input,
    meta: metaUrl ? { url: metaUrl } : {}
  }), [appId, task, input, metaUrl]);

  async function run() {
    setLoading(true);
    setResp(null);
    try {
      const r = await fetch("/api/run", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await r.json();
      setResp(data);
    } catch (e: any) {
      setResp({ ok: false, provider: "client", output: { summary: "", score: 0, flags: ["CLIENT_ERROR"], draft: "" }, error: e?.message ?? "Unknown error" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ padding: 20, maxWidth: 1000, margin: "0 auto" }}>
      <h1 style={{ marginTop: 0 }}>AI Router Console</h1>
      <p style={{ marginTop: 4, opacity: 0.8 }}>
        This is a test UI. Your real apps should call <code>/api/run</code>.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <label>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>appId</div>
          <input value={appId} onChange={e => setAppId(e.target.value)} style={{ width: "100%", padding: 10 }} />
        </label>

        <label>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>task</div>
          <input value={task} onChange={e => setTask(e.target.value)} style={{ width: "100%", padding: 10 }} />
        </label>

        <label style={{ gridColumn: "1 / -1" }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>meta.url (optional)</div>
          <input value={metaUrl} onChange={e => setMetaUrl(e.target.value)} placeholder="https://..." style={{ width: "100%", padding: 10 }} />
        </label>

        <label style={{ gridColumn: "1 / -1" }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>input</div>
          <textarea value={input} onChange={e => setInput(e.target.value)} rows={10} style={{ width: "100%", padding: 10, fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" }} />
        </label>

        <div style={{ gridColumn: "1 / -1", display: "flex", gap: 10 }}>
          <button onClick={run} disabled={loading} style={{ padding: "10px 14px", fontWeight: 700 }}>
            {loading ? "Running..." : "Run"}
          </button>
          <a href="/api/health" target="_blank" rel="noreferrer" style={{ alignSelf: "center" }}>
            /api/health
          </a>
        </div>

        <div style={{ gridColumn: "1 / -1" }}>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>Response</div>
          <pre style={{ background: "#0b0f19", color: "#e6edf3", padding: 14, borderRadius: 8, overflowX: "auto" }}>
{resp ? JSON.stringify(resp, null, 2) : "—"}
          </pre>
        </div>
      </div>
    </main>
  );
}
