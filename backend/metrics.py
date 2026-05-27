"""
Metrics collection and Prometheus instrumentation.
100% Operational, Zero-Cost FOSS implementation.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import psutil

# Core Metrics
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP Requests", ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP Request Latency", ["method", "endpoint"]
)
SYSTEM_CPU = Gauge("system_cpu_usage", "CPU Usage Percentage")
SYSTEM_MEMORY = Gauge("system_memory_usage", "Memory Usage Percentage")
BUILD_COUNTER = Counter("swarm_builds_total", "Total production cycles started")
USAGE_COUNTER = Counter("swarm_usage_events_total", "Total usage events recorded")
BUILD_DURATION = Histogram("swarm_build_duration_seconds", "Duration of production cycles")

def track_request(method: str, endpoint: str, status: int, latency: float):
    """Tracks HTTP request metrics."""
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)

def update_system_metrics():
    """Updates system-level metrics."""
    SYSTEM_CPU.set(psutil.cpu_percent())
    SYSTEM_MEMORY.set(psutil.virtual_memory().percent)

def get_metrics_response():
    """Returns Prometheus-formatted metrics."""
    update_system_metrics()
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
