"""Metricas de latencia via OpenTelemetry Metrics API (Principio VIII, T024)."""

from __future__ import annotations

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource


def configure_metrics(service_name: str = "checkout") -> MeterProvider:
    resource = Resource.create({SERVICE_NAME: service_name})
    reader = PeriodicExportingMetricReader(ConsoleMetricExporter())
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)
    return provider


_meter = metrics.get_meter("checkout.api")

checkout_sessions_latency_ms = _meter.create_histogram(
    name="checkout_sessions_latency_ms",
    unit="ms",
    description="Latencia dos endpoints de checkout-sessions",
)
