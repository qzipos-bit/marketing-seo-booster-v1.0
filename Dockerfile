FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY templates ./templates
COPY static ./static
COPY prompts ./prompts
COPY config.yaml config.quickex.yaml config.altcoinlog.yaml ./
COPY run_check.py ./

RUN useradd -m -u 1000 msb && mkdir -p /app/data/backups && chown -R msb:msb /app
USER msb

ENV ENV=production \
    MONITOR_HOST=0.0.0.0 \
    MONITOR_PORT=8787 \
    PYTHONUNBUFFERED=1

EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://127.0.0.1:8787/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8787", "--workers", "1"]
