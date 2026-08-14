#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB="${ROOT}/data/monitor.db"
DEST="${ROOT}/data/backups"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$DEST"

if [ ! -f "$DB" ]; then
  echo "No database at $DB — skip backup"
  exit 0
fi

OUT="${DEST}/monitor-${STAMP}.db"
sqlite3 "$DB" ".backup '${OUT}'"
echo "Backup: ${OUT}"

# retention: 30 days
find "$DEST" -name 'monitor-*.db' -mtime +30 -delete 2>/dev/null || true
