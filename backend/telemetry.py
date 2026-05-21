import os
import logging

logger = logging.getLogger("SwarmOS.telemetry")


def init():
    disabled = os.getenv("OTEL_SDK_DISABLED", "FALSE").lower() in ("1", "true", "yes")
    if disabled:
        logger.info("OpenTelemetry disabled via OTEL_SDK_DISABLED")
        return
    try:
        # Initialize OpenTelemetry if available; fall back to console exporter
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

        provider = TracerProvider(resource=Resource.create({"service.name": "swarmos"}))
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        logger.info("OpenTelemetry initialized (Console exporter)")
    except Exception as e:
        logger.warning(f"OpenTelemetry not initialized: {e}")
