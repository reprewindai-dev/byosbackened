#!/usr/bin/env sh
set -eu

if command -v alembic >/dev/null 2>&1; then
  alembic upgrade head
fi

python scripts/seed_marketplace_first_party.py || {
  echo "warning: first-party marketplace seed failed; continuing startup" >&2
}

exec gunicorn apps.api.main:app -c gunicorn_conf.py
