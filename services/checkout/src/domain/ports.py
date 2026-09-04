"""Portas (interfaces) do dominio do checkout - Principio I da constituicao.

Adapters concretos (SQLAlchemy, aiokafka) implementam estas interfaces em
src/adapters/outbound/*. O dominio e os casos de uso dependem apenas destas
abstracoes, nunca de uma biblioteca de infraestrutura especifica.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.entities import CheckoutSession


class CheckoutSessionRepository(Protocol):
    """Persiste uma CheckoutSession e o evento de outbox correspondente atomicamente.

    A implementacao concreta e responsavel por gravar a sessao e o registro de
    outbox na MESMA transacao de banco (Principio III - outbox transacional,
    NON-NEGOTIABLE).
    """

    async def salvar(self, session: CheckoutSession) -> None: ...

    async def buscar_por_id(self, session_id: UUID) -> CheckoutSession | None: ...


class EventPublisher(Protocol):
    """Publica um payload de evento ja serializado em um topico Kafka."""

    async def publicar(self, topico: str, chave: str, payload: bytes) -> None: ...
