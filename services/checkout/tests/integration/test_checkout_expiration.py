"""Teste de integracao - Acceptance Scenario 4 do spec.md (T016).

Verifica que o status muda para EXPIRADO na consulta apos expires_at, sem
depender de nenhum job de background (status e derivado na leitura - ver
data-model.md).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.adapters.outbound.messaging.kafka_publisher import FakeEventPublisher
from src.adapters.outbound.persistence.repository import SqlAlchemyCheckoutSessionRepository
from src.domain.entities import CartItemSnapshot, CheckoutSession
from src.main import create_app


async def test_sessao_expirada_e_refletida_na_consulta(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    repository = SqlAlchemyCheckoutSessionRepository(session_factory)

    sessao_ja_expirada = CheckoutSession(
        cart_id="cart-expirado",
        items=(CartItemSnapshot(product_id="sku-1", quantity=1, unit_price=Decimal("1")),),
        created_at=datetime.now(UTC) - timedelta(minutes=20),
    )
    await repository.salvar(sessao_ja_expirada)

    app = create_app()
    app.state.checkout_repository = repository
    app.state.event_publisher = FakeEventPublisher()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(f"/v1/checkout-sessions/{sessao_ja_expirada.session_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "EXPIRADO"


async def test_sessao_recem_criada_nao_esta_expirada(api_client: AsyncClient) -> None:
    payload = {
        "cart_id": "cart-fresco",
        "items": [{"product_id": "sku-1", "quantity": 1, "unit_price": 1.0}],
    }

    created = (await api_client.post("/v1/checkout-sessions", json=payload)).json()

    assert created["status"] == "INICIADO"
