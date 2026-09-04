"""Teste de contrato do evento CheckoutIniciado (T013).

Valida que (a) o modelo Pydantic em libs/contracts serializa exatamente conforme
contracts/events/checkout-iniciado.schema.json, e (b) o payload gravado no
outbox pela feature bate com o mesmo schema (Principio IV da constituicao).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from jsonschema import validate

from contracts.events.checkout_iniciado import CheckoutIniciado
from src.domain.entities import CartItemSnapshot, CheckoutSession

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_PATH = (
    REPO_ROOT
    / "specs"
    / "001-iniciar-checkout"
    / "contracts"
    / "events"
    / "checkout-iniciado.schema.json"
)


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def test_checkout_iniciado_model_matches_schema() -> None:
    evento = CheckoutIniciado(
        saga_id=uuid4(),
        session_id=uuid4(),
        cart_id="cart-123",
        total=Decimal("25.50"),
        expires_at=datetime.now(UTC),
        occurred_at=datetime.now(UTC),
    )

    payload = json.loads(evento.model_dump_json())

    validate(instance=payload, schema=_schema())


def test_event_built_from_checkout_session_matches_schema() -> None:
    from src.adapters.outbound.messaging.event_builder import construir_checkout_iniciado

    session = CheckoutSession.iniciar(
        cart_id="cart-456",
        items=(CartItemSnapshot(product_id="sku-1", quantity=3, unit_price=Decimal("2.00")),),
    )

    evento = construir_checkout_iniciado(session)
    payload = json.loads(evento.model_dump_json())

    validate(instance=payload, schema=_schema())
    assert payload["session_id"] == str(session.session_id)
    assert payload["saga_id"] == str(session.saga_id)
    assert Decimal(payload["total"]) == session.total
