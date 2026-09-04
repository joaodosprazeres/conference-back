"""Adapter SQLAlchemy da porta CheckoutSessionRepository (T018).

Persiste CheckoutSession e o OutboxEvent correspondente NA MESMA transacao
(outbox transacional - Principio III, NON-NEGOTIABLE).
"""

from __future__ import annotations

import json
from datetime import UTC
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.adapters.outbound.messaging.event_builder import construir_checkout_iniciado
from src.adapters.outbound.persistence.models import CheckoutSessionModel, OutboxEventModel
from src.domain.entities import CartItemSnapshot, CheckoutSession


class SqlAlchemyCheckoutSessionRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def salvar(self, session: CheckoutSession) -> None:
        evento = construir_checkout_iniciado(session)

        async with self._session_factory() as db_session:
            async with db_session.begin():
                db_session.add(
                    CheckoutSessionModel(
                        session_id=session.session_id,
                        cart_id=session.cart_id,
                        items=[
                            {
                                "product_id": item.product_id,
                                "quantity": item.quantity,
                                "unit_price": str(item.unit_price),
                            }
                            for item in session.items
                        ],
                        total=session.total,
                        created_at=session.created_at,
                        expires_at=session.expires_at,
                    )
                )
                db_session.add(
                    OutboxEventModel(
                        event_id=uuid4(),
                        event_type=evento.event_type,
                        payload=json.loads(evento.model_dump_json()),
                        status="PENDENTE",
                        attempt_count=0,
                        created_at=evento.occurred_at,
                    )
                )

    async def buscar_por_id(self, session_id: UUID) -> CheckoutSession | None:
        async with self._session_factory() as db_session:
            row = await db_session.get(CheckoutSessionModel, session_id)
            if row is None:
                return None

            items = tuple(
                CartItemSnapshot(
                    product_id=str(item["product_id"]),
                    quantity=int(str(item["quantity"])),
                    unit_price=Decimal(str(item["unit_price"])),
                )
                for item in row.items
            )
            return CheckoutSession(
                cart_id=row.cart_id,
                items=items,
                session_id=row.session_id,
                created_at=row.created_at.astimezone(UTC),
            )
