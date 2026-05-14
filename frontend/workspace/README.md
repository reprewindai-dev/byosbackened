# Veklom Workspace React App

Status: non-production / historical workspace app unless Anthony explicitly approves a future migration.

## Important production warning

This folder is not the current `https://veklom.com` production artifact.

The current accepted `.com` artifact is:

`C:\Users\antho\OneDrive\Desktop\.windsurf\byosbackened\backend\landing`

The current accepted `.com` shell is:

`C:\Users\antho\OneDrive\Desktop\.windsurf\byosbackened\backend\landing\workspace-app.html`

The current accepted `.com` asset bundle is:

- `backend\landing\workspace-assets\index-EUKZeqk4.js`
- `backend\landing\workspace-assets\index-WqgIFi2m.css`

Do not deploy this folder's `dist` output to `veklom.com` unless Anthony explicitly approves replacing the accepted black/orange artifact.

## What this folder is

This folder contains a React/Vite workspace implementation from earlier development work. It may be useful as reference or future migration material, but it is not the `.com` source of truth today.

Historical capabilities included here:

- React 18 + TypeScript + Vite
- Tailwind CSS
- React Router
- TanStack Query
- Zustand auth store
- JWT auth shell
- Workspace route pages

## What not to do

- Do not call this the live `.com` production artifact.
- Do not deploy `frontend\workspace\dist` to Cloudflare Pages project `veklom`.
- Do not use this folder to replace the black/orange `backend\landing` artifact.
- Do not rebuild this folder to imitate the source-of-truth screenshots.

## If this folder is used later

If Anthony explicitly approves a future migration, the migration must be handled as a separate production cutover with:

- Backend route audit
- Visual source-of-truth comparison against the black/orange screenshots
- Auth and API verification
- Cloudflare preview deploy first
- Explicit approval before production deploy

Until then, `.com` remains `backend\landing`.
