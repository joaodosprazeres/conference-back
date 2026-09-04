"""Testes unitarios das invariantes de dominio (T014) - sem I/O."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src.domain.entities import (
    CartItemSnapshot,
    CheckoutSession,
    CheckoutSessionStatus,
    DomainError,
)


def test_cart_item_snapshot_rejects_non_positive_quantity() -> None:
    with pytest.raises(DomainError):
        CartItemSnapshot(product_id="sku-1", quantity=0, unit_price=Decimal("10"))


def test_cart_item_snapshot_rejects_negative_price() -> None:
    with pytest.raises(DomainError):
        CartItemSnapshot(product_id="sku-1", quantity=1, unit_price=Decimal("-1"))


def test_checkout_session_requires_at_least_one_item() -> None:
    with pytest.raises(DomainError):
        CheckoutSession.iniciar(cart_id="cart-1", items=())


def test_total_is_sum_of_quantity_times_unit_price() -> None:
    items = (
        CartItemSnapshot(product_id="sku-1", quantity=2, unit_price=Decimal("10.00")),
        CartItemSnapshot(product_id="sku-2", quantity=3, unit_price=Decimal("1.50")),
    )

    session = CheckoutSession.iniciar(cart_id="cart-1", items=items)

    assert session.total == Decimal("24.50")


def test_expires_at_is_created_at_plus_15_minutes() -> None:
    items = (CartItemSnapshot(product_id="sku-1", quantity=1, unit_price=Decimal("1")),)

    session = CheckoutSession.iniciar(cart_id="cart-1", items=items)

    assert session.expires_at == session.created_at + timedelta(minutes=15)


def test_status_is_iniciado_before_expiration() -> None:
    items = (CartItemSnapshot(product_id="sku-1", quantity=1, unit_price=Decimal("1")),)
    session = CheckoutSession.iniciar(cart_id="cart-1", items=items)

    momento = session.created_at + timedelta(minutes=5)

    assert session.status_em(momento) == CheckoutSessionStatus.INICIADO


def test_status_is_expirado_after_expiration() -> None:
    items = (CartItemSnapshot(product_id="sku-1", quantity=1, unit_price=Decimal("1")),)
    session = CheckoutSession.iniciar(cart_id="cart-1", items=items)

    momento = session.created_at + timedelta(minutes=16)

    assert session.status_em(momento) == CheckoutSessionStatus.EXPIRADO


def test_saga_id_equals_session_id() -> None:
    items = (CartItemSnapshot(product_id="sku-1", quantity=1, unit_price=Decimal("1")),)
    session = CheckoutSession.iniciar(cart_id="cart-1", items=items)

    assert session.saga_id == session.session_id
