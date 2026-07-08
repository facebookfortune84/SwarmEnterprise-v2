FROM python:3.11-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y dos2unix curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir email-validator pyjwt bcrypt && pip install --user --no-cache-dir -r requirements.txt

# -------------------------

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y dos2unix curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV SWARM_REPO_ROOT=/app
ENV SWARM_OUTPUT_DIR=/app/output

COPY backend/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh && dos2unix /docker-entrypoint.sh

HEALTHCHECK --interval=15s --timeout=5s --retries=3 --start-period=30s \
  CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
