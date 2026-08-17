# Production administration

Application directory: `/opt/marketing-seo-booster`.

Production URL: `https://seo.gizli.ru`.

## Status

```bash
cd /opt/marketing-seo-booster
docker compose ps
curl -fsS http://127.0.0.1:8787/health
```

## Logs

```bash
cd /opt/marketing-seo-booster
docker compose logs -f msb
```

## Restart

```bash
cd /opt/marketing-seo-booster
docker compose restart msb
```

Full restart, including the backup service:

```bash
cd /opt/marketing-seo-booster
docker compose --profile backup down
docker compose --profile backup up -d
```

## Update

```bash
cd /opt/marketing-seo-booster
docker compose exec backup /scripts/backup_db.sh
git pull --ff-only
docker compose --profile backup up -d --build
docker compose ps
docker compose logs --tail=100 msb
```

## Backup

The backup service runs every six hours and keeps 30 days of SQLite backups in
`/opt/marketing-seo-booster/data/backups`.

```bash
cd /opt/marketing-seo-booster
docker compose --profile backup up -d backup
docker compose exec backup /scripts/backup_db.sh
ls -lh data/backups
```

## Nginx, SSL, and firewall

```bash
sudo nginx -t
sudo systemctl reload nginx
sudo certbot certificates
sudo ufw status verbose
```

Secrets are stored only in `/opt/marketing-seo-booster/.env` (mode `600`).

## Automatic deployment

Pushes to `main` run Tests, Docker build validation, SQLite backup, exact-commit
deployment, local healthcheck, and HTTPS healthcheck in GitHub Actions.

1. Commit the changes.
2. Push `main`.
3. Open GitHub → Actions → CI/CD and wait for the green workflow.

### Manual deployment

Open GitHub → Actions → CI/CD → Run workflow and select `main`. Manual runs pass
the same tests and Docker validation before production deployment.

### Failed deployment

If the new container does not become healthy, the deployment script restores the
previous working commit and rebuilds it. The GitHub workflow still remains failed.
The pre-deployment SQLite backup is retained; the database is not restored
automatically.

### GitHub configuration

Secrets: `DEPLOY_HOST`, `DEPLOY_PORT`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`,
`DEPLOY_KNOWN_HOSTS`.

Variable: `PRODUCTION_URL`.

The workflow transfers the exact commit as a Git bundle over SSH, so deployment
continues to work if the repository becomes private. No GitHub PAT or repository
private key is stored on the server.

Production CI/CD was verified with consecutive deployments on 2026-08-17.
