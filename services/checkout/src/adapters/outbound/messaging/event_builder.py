"""Constroi o evento CheckoutIniciado (libs/contracts) a partir da entidade de
dominio CheckoutSession. Unico ponto de traducao dominio -> contrato de evento."""

from __future__ import annotations

from datetime import UTC, datetime

from contracts.events.checkout_iniciado import CheckoutIniciado
from src.domain.entities import CheckoutSession


def construir_checkout_iniciado(session: CheckoutSession) -> CheckoutIniciado:
    return CheckoutIniciado(
        saga_id=session.saga_id,
        session_id=session.session_id,
        cart_id=session.cart_id,
        total=session.total,
        expires_at=session.expires_at,
        occurred_at=datetime.now(UTC),
    )
