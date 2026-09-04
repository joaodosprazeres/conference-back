"""Schemas Pydantic de request/response da API (T021), espelhando
contracts/openapi.yaml. `extra="forbid"` em IniciarCheckoutRequest garante que
campos fora de escopo (email, payment_method, coupon - FR-006/007/008) sejam
rejeitados, nao apenas ignorados."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ItemCarrinho(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: str
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class IniciarCheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cart_id: str
    items: list[ItemCarrinho] = Field(min_length=1)


class CheckoutSessionResponse(BaseModel):
    session_id: UUID
    cart_id: str
    status: str
    total: Decimal
    expires_at: datetime
