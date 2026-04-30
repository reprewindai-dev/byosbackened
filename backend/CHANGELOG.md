# Changelog

## Unreleased

### Added
- Amazon Bedrock AI completion endpoint at `POST /api/v1/ai/complete` with JWT auth, wallet balance enforcement, token deduction, and audit logging.
- Workspace dashboard AI Playground section with model selector, prompt input, live token balance, free-tier lockout, and response cost display.
- Hetzner Postgres backup automation for S3, including an install script, daily 02:00 UTC cron entry, and 7-day S3 retention cleanup.
- AWS environment variables for Bedrock and backup automation in the backend env templates.
- Workspace dashboard rebuilt into a tabbed AI gateway control plane with overview metrics, observability, API keys, model toggles, and cost/budget views.
- Public `/status` page and public status JSON endpoint for API, Auth, Marketplace, and AI Proxy uptime and incident visibility.
- Normalized workspace request logging for API key usage, AI completions, observability charts, and cost exports.
- Added Edge execution layer (`/api/v1/edge/...`) with webhook intake, normalized `EdgeMessage`, baseline rule engine (`temperature > 80` alert), and route adapters for AI/API outputs.
