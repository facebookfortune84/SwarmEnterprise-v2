#!/bin/bash
set -e

echo "=========================================="
echo " SwarmOS Backend Startup"
echo "=========================================="

if [ -f "/app/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source /app/.env
  set +a
fi

if [ -n "${OLLAMA_URL}" ]; then
  echo "Waiting for Ollama at ${OLLAMA_URL}..."
  MAX_RETRIES=30
  RETRY_COUNT=0
  while [ "$RETRY_COUNT" -lt "$MAX_RETRIES" ]; do
    if curl -sf "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
      echo "Ollama is ready"
      break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 2
  done
fi

exec "$@"
