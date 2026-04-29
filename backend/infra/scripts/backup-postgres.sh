#!/usr/bin/env bash
# Veklom Postgres backup job
#
# Expected env vars:
# - DATABASE_URL
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - AWS_DEFAULT_REGION
# - S3_BACKUP_BUCKET
#
# Optional env vars:
# - BACKUP_DIR (default: /var/backups/veklom)

set -euo pipefail

umask 077

BACKUP_DIR="${BACKUP_DIR:-/var/backups/veklom}"
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
S3_BACKUP_BUCKET="${S3_BACKUP_BUCKET:-veklom-db-backups}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RAW_DUMP="${BACKUP_DIR}/veklom-postgres-${TIMESTAMP}.sql"
ARCHIVE="${RAW_DUMP}.gz"
S3_KEY="postgres/${TIMESTAMP}/$(basename "${ARCHIVE}")"
ENV_FILE="/etc/veklom/backup.env"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

: "${DATABASE_URL:?DATABASE_URL must be configured}"
: "${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID must be configured}"
: "${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY must be configured}"
: "${AWS_DEFAULT_REGION:?AWS_DEFAULT_REGION must be configured}"
: "${S3_BACKUP_BUCKET:?S3_BACKUP_BUCKET must be configured}"

mkdir -p "${BACKUP_DIR}"

echo "[veklom-backup] dumping postgres at $(date -u --iso-8601=seconds)"
pg_dump "${DATABASE_URL}" --no-owner --no-privileges > "${RAW_DUMP}"
gzip -f "${RAW_DUMP}"

echo "[veklom-backup] uploading ${ARCHIVE} to s3://${S3_BACKUP_BUCKET}/${S3_KEY}"
aws s3 cp "${ARCHIVE}" "s3://${S3_BACKUP_BUCKET}/${S3_KEY}" --region "${AWS_DEFAULT_REGION}"

rm -f "${ARCHIVE}"

echo "[veklom-backup] pruning objects older than 7 days"
python3 - "${S3_BACKUP_BUCKET}" "${AWS_DEFAULT_REGION}" <<'PY'
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

bucket = sys.argv[1]
region = sys.argv[2]
cutoff = datetime.now(timezone.utc) - timedelta(days=7)

listing = subprocess.check_output(
    [
        "aws",
        "s3api",
        "list-objects-v2",
        "--bucket",
        bucket,
        "--prefix",
        "postgres/",
        "--region",
        region,
        "--output",
        "json",
    ],
    text=True,
)
payload = json.loads(listing or "{}")
for item in payload.get("Contents", []):
    last_modified = item.get("LastModified")
    key = item.get("Key")
    if not last_modified or not key:
        continue
    lm = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
    if lm < cutoff:
        subprocess.check_call(
            [
                "aws",
                "s3api",
                "delete-object",
                "--bucket",
                bucket,
                "--key",
                key,
                "--region",
                region,
            ]
        )
PY

echo "[veklom-backup] completed successfully at $(date -u --iso-8601=seconds)"
