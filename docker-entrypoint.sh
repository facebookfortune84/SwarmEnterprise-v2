#!/bin/bash

set -e

echo "==========================================
echo " SwarmOS Backend Startup"
echo "=========================================="

# Load environment
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Wait for Ollama to be ready (with retries)
echo "Waiting for Ollama at ${OLLAMA_URL}..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
        echo "✓ Ollama is ready!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "  Retry $RETRY_COUNT/$MAX_RETRIES..."
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "⚠ Warning: Ollama not ready after 60 seconds. Continuing anyway..."
fi

# Run migrations (if using alembic, uncomment)
# echo "Running database migrations..."
# alembic upgrade head

# Start application
echo "Starting SwarmOS Backend..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000