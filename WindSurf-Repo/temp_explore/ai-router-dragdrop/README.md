# AI Router (Drag-and-Drop Deploy)

This is a **single Next.js project** that includes:
- A minimal UI (test console)
- A backend **router API** on Vercel: `POST /api/run`
- A health endpoint: `GET /api/health`

## Deploy (fastest path)
1) Upload this folder to GitHub (or import directly to Vercel).
2) Deploy on Vercel.
3) Set environment variables in Vercel:
   - `ROUTER_PROVIDER=mock` (default) OR `serpapi`
   - If using SerpApi: `SERPAPI_KEY=...`

## Use
Open the deployed site → paste input → choose `appId` → click Run.

## Important
- This is intentionally **provider-pluggable**.
- You can add more providers in `src/lib/providers/*`.
- Your other apps should call `/api/run` instead of calling models directly.

## API contract
### POST /api/run
Body:
```json
{
  "appId": "lead-radar",
  "task": "score_and_draft",
  "input": "raw text here",
  "meta": { "url": "https://example.com" }
}
```

Response (always):
```json
{
  "ok": true,
  "provider": "mock",
  "output": { "summary":"...", "score": 0, "flags": ["OK"], "draft": "..." },
  "raw": null
}
```

If provider errors/throttles:
- `ok: false` but `output` is still present (fallback), with `flags` including `AI_DOWN` or similar.

