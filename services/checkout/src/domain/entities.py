"""Entidades de dominio da feature Iniciar Checkout.

Este modulo NAO importa FastAPI, SQLAlchemy, aiokafka nem qualquer biblioteca de
infraestrutura (Principio I da constituicao, NON-NEGOTIABLE). Apenas tipos padrao
e Pydantic para representacao de dados sao usados aqui.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

SESSAO_EXPIRACAO_MINUTOS = 15


class CheckoutSessionStatus(StrEnum):
    INICIADO = "INICIADO"
    EXPIRADO = "EXPIRADO"


class DomainError(ValueError):
    """Erro de violacao de invariante de dominio."""


@dataclass(frozen=True, slots=True)
class CartItemSnapshot:
    """Item do carrinho capturado no momento do inicio do checkout (FR-012)."""

    product_id: str
    quantity: int
    unit_price: Decimal

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise DomainError("quantity deve ser maior que zero")
        if self.unit_price < 0:
            raise DomainError("unit_price nao pode ser negativo")

    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass(frozen=True, slots=True)
class CheckoutSession:
    """Sessao de checkout iniciada a partir de um carrinho (spec.md - Key Entities)."""

    cart_id: str
    items: tuple[CartItemSnapshot, ...]
    session_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expiration_minutes: int = SESSAO_EXPIRACAO_MINUTOS

    def __post_init__(self) -> None:
        if not self.items:
            raise DomainError("uma sessao de checkout precisa de ao menos um item")

    @property
    def saga_id(self) -> UUID:
        """O session_id tambem atua como saga_id desta feature em diante (Principio V)."""
        return self.session_id

    @property
    def total(self) -> Decimal:
        return sum((item.subtotal for item in self.items), start=Decimal("0"))

    @property
    def expires_at(self) -> datetime:
        return self.created_at + timedelta(minutes=self.expiration_minutes)

    def status_em(self, momento: datetime) -> CheckoutSessionStatus:
        """Status derivado por comparacao com expires_at (ver data-model.md)."""
        if momento >= self.expires_at:
            return CheckoutSessionStatus.EXPIRADO
        return CheckoutSessionStatus.INICIADO

    @classmethod
    def iniciar(cls, cart_id: str, items: tuple[CartItemSnapshot, ...]) -> CheckoutSession:
        return cls(cart_id=cart_id, items=items)
