"""Caso de uso IniciarCheckout (T017).

Depende apenas das portas do dominio (Principio I) - nao conhece FastAPI,
SQLAlchemy nem Kafka.
"""

from __future__ import annotations

from src.domain.entities import CartItemSnapshot, CheckoutSession
from src.domain.ports import CheckoutSessionRepository


class IniciarCheckout:
    def __init__(self, repository: CheckoutSessionRepository) -> None:
        self._repository = repository

    async def executar(
        self, cart_id: str, items: tuple[CartItemSnapshot, ...]
    ) -> CheckoutSession:
        session = CheckoutSession.iniciar(cart_id=cart_id, items=items)
        await self._repository.salvar(session)
        return session
