"""Modelos SQLAlchemy 2.x para persistencia do checkout (data-model.md).

Estes modelos vivem no adapter de persistencia, nunca no dominio (Principio I).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CheckoutSessionModel(Base):
    __tablename__ = "checkout_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    cart_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    items: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OutboxEventModel(Base):
    """Registro tecnico de outbox (Principio III, NON-NEGOTIABLE).

    status: "PENDENTE" | "PUBLICADO" | "FALHOU"
    Apos exceder max_attempts tentativas, o relay marca "FALHOU" e publica o
    payload original no topico de DLQ (ver outbox_relay.py e data-model.md).
    """

    __tablename__ = "outbox_events"

    event_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDENTE", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
