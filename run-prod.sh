#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Создан .env — добавь KIE_API_KEY и перезапусти."
fi

export ENV="${ENV:-production}"
echo "Marketing SEO Booster v1.0 (production) — http://${MONITOR_HOST:-127.0.0.1}:${MONITOR_PORT:-8787}"

exec uvicorn app.main:app \
  --host "${MONITOR_HOST:-127.0.0.1}" \
  --port "${MONITOR_PORT:-8787}" \
  --workers 1
