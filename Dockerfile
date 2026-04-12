# Build from repository root (required for automated HF / CI docker builds).
#   docker build -t sqla-env .
FROM python:3.11-slim

LABEL space.sdk="docker"
LABEL space.tags="openenv,sql,security,database,rl"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY sqla-env/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sqla-env/app/ ./app/
COPY sqla-env/openenv.yaml .
COPY inference.py .

EXPOSE 7860

ENV PORT=7860
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

CMD ["python", "-m", "uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "7860"]
