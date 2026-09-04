"""Composition root do servico checkout - monta o app FastAPI e faz o wiring
dos adapters concretos as portas do dominio (Principio I)."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.adapters.inbound.api.routers import router
from src.adapters.observability.logging import configure_logging, get_logger
from src.adapters.observability.metrics import configure_metrics
from src.adapters.observability.tracing import configure_tracing
from src.adapters.outbound.messaging.kafka_publisher import KafkaEventPublisher
from src.adapters.outbound.messaging.outbox_relay import OutboxRelayWorker
from src.adapters.outbound.persistence.db import create_engine, create_session_factory
from src.adapters.outbound.persistence.repository import SqlAlchemyCheckoutSessionRepository

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    configure_tracing()
    configure_metrics()
    logger.info("checkout.startup")

    start = getattr(app.state.event_publisher, "start", None)
    if callable(start):
        await start()

    relay = OutboxRelayWorker(app.state.session_factory, app.state.event_publisher)
    relay_task = asyncio.create_task(relay.run_forever())

    yield

    relay_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await relay_task

    stop = getattr(app.state.event_publisher, "stop", None)
    if callable(stop):
        await stop()

    logger.info("checkout.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Checkout Service API",
        version="1.0",
        lifespan=lifespan,
    )

    engine = create_engine()
    session_factory = create_session_factory(engine)
    app.state.session_factory = session_factory
    app.state.checkout_repository = SqlAlchemyCheckoutSessionRepository(session_factory)
    app.state.event_publisher = KafkaEventPublisher()

    app.include_router(router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
