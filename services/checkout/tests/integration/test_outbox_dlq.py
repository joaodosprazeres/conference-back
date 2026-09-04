"""Teste de integracao - DLQ do OutboxRelayWorker (T025, resolve D1 da analise).

Verifica que uma falha persistente de publicacao no topico principal resulta em
status=FALHOU apos max_attempts tentativas, e que o payload original e
publicado no topico de DLQ (checkout.outbox.dlq) - Principio III, NON-NEGOTIABLE.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.adapters.outbound.messaging.kafka_publisher import FakeEventPublisher
from src.adapters.outbound.messaging.outbox_relay import (
    TOPICO_CHECKOUT_EVENTOS,
    TOPICO_DLQ,
    OutboxRelayWorker,
)
from src.adapters.outbound.persistence.models import OutboxEventModel
from src.adapters.outbound.persistence.repository import SqlAlchemyCheckoutSessionRepository
from src.domain.entities import CartItemSnapshot, CheckoutSession


async def test_falha_persistente_marca_falhou_e_publica_na_dlq(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = SqlAlchemyCheckoutSessionRepository(session_factory)
    session = CheckoutSession.iniciar(
        cart_id="cart-dlq",
        items=(CartItemSnapshot(product_id="sku-1", quantity=1, unit_price=Decimal("1")),),
    )
    await repository.salvar(session)

    publisher = FakeEventPublisher(falhar_topicos={TOPICO_CHECKOUT_EVENTOS})
    relay = OutboxRelayWorker(session_factory, publisher, max_attempts=2)

    for _ in range(2):
        await relay.processar_pendentes()

    async with session_factory() as db_session:
        result = await db_session.execute(select(OutboxEventModel))
        evento = result.scalars().one()

    assert evento.status == "FALHOU"
    assert evento.attempt_count == 2

    topicos_publicados = [msg[0] for msg in publisher.mensagens]
    assert TOPICO_DLQ in topicos_publicados


async def test_publicacao_bem_sucedida_marca_publicado(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = SqlAlchemyCheckoutSessionRepository(session_factory)
    session = CheckoutSession.iniciar(
        cart_id="cart-ok",
        items=(CartItemSnapshot(product_id="sku-1", quantity=1, unit_price=Decimal("1")),),
    )
    await repository.salvar(session)

    publisher = FakeEventPublisher()
    relay = OutboxRelayWorker(session_factory, publisher)

    publicados = await relay.processar_pendentes()

    assert publicados == 1
    async with session_factory() as db_session:
        result = await db_session.execute(select(OutboxEventModel))
        evento = result.scalars().one()
    assert evento.status == "PUBLICADO"
    assert evento.published_at is not None
