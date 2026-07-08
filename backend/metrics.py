from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

REQUESTS = Counter("requests_total", "Total requests", ["method", "endpoint", "status"])
REQUEST_DURATION = Histogram("request_duration_seconds", "Request duration in seconds", ["method", "endpoint"])


def track_request(method: str, endpoint: str, status: int, duration: float):
    """Track a request in Prometheus metrics."""
    REQUESTS.labels(method=method, endpoint=endpoint, status=status).inc()
    REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)


def get_metrics_response():
    """Return Prometheus metrics in text format."""
    return generate_latest()
