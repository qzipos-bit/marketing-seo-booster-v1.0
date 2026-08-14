.PHONY: dev prod test docker-up docker-down backup lint

dev:
	./run.sh

prod:
	ENV=production ./run-prod.sh

test:
	.venv/bin/pytest tests/ -q

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-backup:
	docker compose --profile backup up -d backup

backup:
	chmod +x scripts/backup_db.sh && ./scripts/backup_db.sh

lint:
	.venv/bin/python -m compileall app
