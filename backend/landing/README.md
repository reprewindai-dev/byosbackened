# Veklom Landing / Workspace Static Deploy

This directory is the Cloudflare Pages production deploy directory for `veklom.com`.

## Production deploy directory

`backend/landing`

## Accepted workspace artifact

The accepted black/orange Veklom workspace loads from:

- `workspace-assets/index-CS55LKkt.js`
- `workspace-assets/index-C-K5tu-A.css`

The route shell is:

- `workspace-app.html`

All workspace routes under this directory must load those two exact assets.

## Workspace routes

The deployed workspace app is one artifact under `/login/`.

- `/login/#/`
- `/login/#/playground`
- `/login/#/marketplace`
- `/login/#/models`
- `/login/#/pipelines`
- `/login/#/deployments`
- `/login/#/vault`
- `/login/#/compliance`
- `/login/#/monitoring`
- `/login/#/billing`
- `/login/#/team`
- `/login/#/settings`
- `/login/#/gpc`

Root clean paths redirect to the matching `/login/#/...` route and must not
serve separate workspace artifacts. `/login/#/monitoring` is the canonical
verification route and must show `Real-time observability`.

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
