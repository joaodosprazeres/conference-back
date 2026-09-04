"""Contrato do evento CheckoutIniciado (Principio IV da constituicao).

Modelo Pydantic versionado, compartilhado por todos os servicos do monorepo que
produzem ou consomem este evento. Qualquer mudanca de campo obrigatorio deve
quebrar os testes de contrato antes do merge (ver services/checkout/tests/contract).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

EVENT_TYPE: Literal["CheckoutIniciado"] = "CheckoutIniciado"
EVENT_VERSION: Literal["1.0"] = "1.0"


class CheckoutIniciado(BaseModel):
    """Evento informativo publicado quando uma sessao de checkout e criada."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_type: Literal["CheckoutIniciado"] = EVENT_TYPE
    event_version: Literal["1.0"] = EVENT_VERSION
    saga_id: UUID
    session_id: UUID
    cart_id: str
    total: Decimal
    expires_at: datetime
    occurred_at: datetime
