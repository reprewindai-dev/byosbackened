# Agent Access

This file is the operational handoff for agent-driven work.

## Rule Of Engagement

- The agent does the work end to end.
- Do not ask the user to locate credentials, hostnames, or dashboard paths unless the repo truly lacks them.
- Prefer the repo and the live host over memory.
- If a live container is failing, inspect the container logs before changing code.

## Source Of Truth

- `main` is the source of truth for code.
- Live Veklom production host is `5.78.135.11`.
- Live CO2 Router / ECOBE host is `5.78.153.146`.

## SSH Access

Use the deploy key already present in the workspace:

```bash
ssh -F NUL -i ~/.ssh/veklom-deploy root@5.78.135.11
ssh -F NUL -i ~/.ssh/veklom-deploy root@5.78.153.146
```

If SSH fails on Windows because of local `~/.ssh/config` permissions, bypass the config with `-F NUL` as above.

## Coolify Mapping

- Veklom project: `veklom`
- Veklom API app: `veklom-api`
- Veklom live backend container: `zjhp30ys1jlk8yaoxc96h2zd-213941724689`
- Veklom Ollama container: `veklom-ollama`
- CO2 Router / ECOBE project: `ecobe`
- CO2 Router database resource: `ecobe-postgres`

## Runtime Checks

Before changing runtime config, check the live app container env:

```bash
docker exec <veklom-api-container> env | awk -F= '$1=="DATABASE_URL" || $1=="REDIS_URL" {print}'
```

Before assuming a deploy is healthy, check:

```bash
docker ps
docker logs --tail 80 <container_name>
```

## Bootstrap Flow

- `backend/scripts/bootstrap_prod.sh` is the canonical bootstrap script for the live Veklom host.
- It detects the Postgres and Redis containers on `5.78.135.11`.
- It prints the exact `DATABASE_URL` and `REDIS_URL` values that should be present in `veklom-api`.
- If those env vars are missing, set them in Coolify and redeploy the app.

## Deploy Discipline

- Do not mix the Veklom host with the CO2 Router / ECOBE host.
- Do not assume a restart-looping container is the live one.
- Verify the Coolify resource name before changing anything.
- Keep secrets out of the repository.

