#!/usr/bin/env bash
set -Eeuo pipefail

TARGET_COMMIT="${1:?usage: deploy_production.sh <commit-sha>}"
APP_DIR="${DEPLOY_PATH:-/opt/marketing-seo-booster}"
PRODUCTION_URL="${PRODUCTION_URL:-https://seo.gizli.ru}"
SERVICE=msb
DEPLOY_STARTED=0

[[ "$TARGET_COMMIT" =~ ^[0-9a-f]{40}$ ]] || {
  echo "Invalid target commit"
  exit 2
}

cd "$APP_DIR"

wait_for_health() {
  local container_id running health
  echo "Waiting for healthcheck"
  for _ in {1..24}; do
    container_id="$(docker compose ps -q "$SERVICE")"
    if [[ -n "$container_id" ]]; then
      running="$(docker inspect -f '{{.State.Running}}' "$container_id" 2>/dev/null || true)"
      health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id" 2>/dev/null || true)"
      if [[ "$running" == true && ( "$health" == healthy || "$health" == none ) ]] \
        && curl -fsS http://127.0.0.1:8787/health >/dev/null; then
        return 0
      fi
    fi
    sleep 5
  done
  return 1
}

rollback() {
  local exit_code=$?
  trap - ERR
  set +e

  if (( DEPLOY_STARTED )); then
    echo "Deployment failed; collecting logs"
    docker compose ps
    docker compose logs --tail=200 "$SERVICE"
    echo "Rolling back to ${PREVIOUS_COMMIT:0:7}"
    git reset --hard "$PREVIOUS_COMMIT"
    docker compose config --quiet \
      && docker compose up -d --build "$SERVICE" \
      && docker compose --profile backup up -d backup \
      && wait_for_health \
      && curl -fsS "$PRODUCTION_URL/health" >/dev/null
    if [[ $? -eq 0 ]]; then
      echo "Rollback restored ${PREVIOUS_COMMIT:0:7}"
    else
      echo "Rollback failed; manual intervention required"
    fi
  fi

  exit "$exit_code"
}
trap rollback ERR

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Production worktree is not clean; refusing to overwrite changes"
  git status --short
  exit 1
fi

PREVIOUS_COMMIT="$(git rev-parse HEAD)"
echo "Current production commit: ${PREVIOUS_COMMIT:0:7}"
echo "Creating database backup"

if [[ -f data/monitor.db ]]; then
  before_count="$(find data/backups -maxdepth 1 -type f -name 'monitor-*.db' | wc -l)"
  docker compose exec -T backup /scripts/backup_db.sh
  after_count="$(find data/backups -maxdepth 1 -type f -name 'monitor-*.db' | wc -l)"
  (( after_count > before_count )) || {
    echo "Database backup was not created"
    exit 1
  }
else
  docker compose exec -T backup /scripts/backup_db.sh
fi

echo "Validating target commit ${TARGET_COMMIT:0:7}"
git cat-file -e "${TARGET_COMMIT}^{commit}"

DEPLOY_STARTED=1
git reset --hard "$TARGET_COMMIT"
[[ "$(git rev-parse HEAD)" == "$TARGET_COMMIT" ]]

echo "Validating Docker Compose"
docker compose config --quiet
echo "Building production container"
docker compose up -d --build "$SERVICE"
echo "Starting backup service"
docker compose --profile backup up -d backup

wait_for_health
docker compose ps

echo "Checking production HTTPS"
curl -fsS "$PRODUCTION_URL/health" >/dev/null
root_status="$(curl -sS -o /dev/null -w '%{http_code}' "$PRODUCTION_URL/")"
[[ "$root_status" != 000 && "$root_status" -lt 500 ]]

trap - ERR
echo "Production deployed commit: ${TARGET_COMMIT:0:7}"
echo "Deployment successful"
