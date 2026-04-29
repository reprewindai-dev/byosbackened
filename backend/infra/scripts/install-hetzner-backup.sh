#!/usr/bin/env bash
# Installs the Veklom Postgres backup job on a Hetzner Ubuntu host.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="/opt/scripts"
TARGET_SCRIPT="${TARGET_DIR}/backup-postgres.sh"
CRON_FILE="/etc/cron.d/veklom-postgres-backup"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root."
  exit 1
fi

apt-get update
apt-get install -y awscli postgresql-client python3

install -d -m 0755 "${TARGET_DIR}"
install -m 0755 "${SCRIPT_DIR}/backup-postgres.sh" "${TARGET_SCRIPT}"
install -d -m 0750 /etc/veklom

if [[ ! -f /etc/veklom/backup.env ]]; then
  cat >/etc/veklom/backup.env <<'EOF'
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1
S3_BACKUP_BUCKET=veklom-db-backups
DATABASE_URL=
EOF
  chmod 0600 /etc/veklom/backup.env
fi

cat >"${CRON_FILE}" <<'EOF'
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
0 2 * * * root /opt/scripts/backup-postgres.sh >> /var/log/veklom-postgres-backup.log 2>&1
EOF

chmod 0644 "${CRON_FILE}"
systemctl restart cron || true

echo "Installed ${TARGET_SCRIPT}"
echo "Fill in /etc/veklom/backup.env and the daily 02:00 UTC cron job will run automatically."
