"""Tracing distribuido via OpenTelemetry (Principio V da constituicao).

saga_id e propagado como atributo de span, permitindo visualizar o fluxo
completo de um checkout - sincrono e assincrono - em uma unica trace.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Span, Tracer

SAGA_ID_ATTRIBUTE = "saga_id"


def configure_tracing(service_name: str = "checkout") -> TracerProvider:
    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    return provider


def get_tracer(name: str = "checkout") -> Tracer:
    return trace.get_tracer(name)


@contextmanager
def start_span_with_saga_id(tracer: Tracer, name: str, saga_id: str) -> Iterator[Span]:
    with tracer.start_as_current_span(name) as span:
        span.set_attribute(SAGA_ID_ATTRIBUTE, saga_id)
        yield span
