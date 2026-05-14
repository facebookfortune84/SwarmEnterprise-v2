from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

BUILD_COUNTER = Counter('swarm_builds_total', 'Total production cycles started')
USAGE_COUNTER = Counter('swarm_usage_events_total', 'Total usage events recorded')
BUILD_DURATION = Histogram('swarm_build_duration_seconds', 'Duration of production cycles')


def metrics_endpoint():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
