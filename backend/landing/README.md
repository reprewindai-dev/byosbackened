# Veklom Landing / Workspace Static Deploy

This directory is the Cloudflare Pages production deploy directory for `veklom.com`.

## Production deploy directory

`backend/landing`

## Accepted workspace artifact

The accepted black/orange Veklom workspace loads from:

- `workspace-assets/index-EUKZeqk4.js`
- `workspace-assets/index-WqgIFi2m.css`

The route shell is:

- `workspace-app.html`

All workspace routes under this directory must load those two exact assets.

## Workspace routes

- `/overview/`
- `/playground/`
- `/marketplace/`
- `/models/`
- `/pipelines/`
- `/deployments/`
- `/vault/`
- `/compliance/`
- `/monitoring/`
- `/billing/`
- `/team/`
- `/settings/`

`/monitoring/` is the canonical verification route and must show `Real-time observability`.

## Rejected files / states

- `workspace-live.js`
- stale workspace hashes
- purple workspace UI
- sparse mimic UI
- `Marketplace transparency`
- `Source verified`

## Deploy

```powershell
wrangler pages deploy backend/landing --project-name veklom --branch main --commit-dirty=true
```

No build step is required for artifact restoration.