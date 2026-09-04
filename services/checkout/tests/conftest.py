"""Fixtures compartilhadas dos testes do servico checkout.

Os testes de integracao/contrato exigem PostgreSQL disponivel (ver
docker-compose.yml e quickstart.md). Quando DATABASE_URL nao esta acessivel, os
testes que dependem dele sao pulados (skip) em vez de falhar o build inteiro.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.adapters.outbound.persistence.db import create_engine, create_session_factory
from src.adapters.outbound.persistence.models import Base
from src.main import create_app


@pytest_asyncio.fixture(scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    eng = create_engine()
    try:
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except SQLAlchemyError:
        pytest.skip(
            "PostgreSQL indisponivel em "
            f"{os.environ.get('DATABASE_URL', '(default)')} - suba docker-compose.yml"
        )
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    factory = create_session_factory(engine)
    yield factory
    # limpeza entre testes: trunca as tabelas usadas pela feature
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.drop_all(sync_conn))
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture
async def api_client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncClient]:
    from src.adapters.outbound.messaging.kafka_publisher import FakeEventPublisher
    from src.adapters.outbound.persistence.repository import SqlAlchemyCheckoutSessionRepository

    app = create_app()
    app.state.checkout_repository = SqlAlchemyCheckoutSessionRepository(session_factory)
    app.state.event_publisher = FakeEventPublisher()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
