"""Teste de contrato da API - valida POST/GET checkout-sessions e GET /health
contra contracts/openapi.yaml (T012).

Cobre tambem a rejeicao de campos nao previstos (FR-006/FR-007/FR-008), garantida
por `extra="forbid"` no schema Pydantic de IniciarCheckoutRequest.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from httpx import AsyncClient
from jsonschema import validate

REPO_ROOT = Path(__file__).resolve().parents[4]
CONTRACTS_DIR = REPO_ROOT / "specs" / "001-iniciar-checkout" / "contracts"
OPENAPI_PATH = CONTRACTS_DIR / "openapi.yaml"


def _load_openapi() -> dict:
    with OPENAPI_PATH.open() as f:
        return yaml.safe_load(f)


def _response_schema(openapi: dict) -> dict:
    schema = openapi["components"]["schemas"]["CheckoutSessionResponse"]
    schema["components"] = openapi["components"]
    return schema


@pytest.fixture(scope="module")
def openapi() -> dict:
    return _load_openapi()


VALID_PAYLOAD = {
    "cart_id": "cart-123",
    "items": [
        {"product_id": "sku-1", "quantity": 2, "unit_price": 10.0},
        {"product_id": "sku-2", "quantity": 1, "unit_price": 5.5},
    ],
}


async def test_post_checkout_sessions_matches_contract(api_client: AsyncClient, openapi: dict) -> None:
    response = await api_client.post("/v1/checkout-sessions", json=VALID_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    validate(instance=body, schema=_response_schema(openapi))
    assert body["status"] == "INICIADO"
    assert float(body["total"]) == pytest.approx(25.5)


async def test_get_checkout_session_matches_contract(api_client: AsyncClient, openapi: dict) -> None:
    created = (await api_client.post("/v1/checkout-sessions", json=VALID_PAYLOAD)).json()

    response = await api_client.get(f"/v1/checkout-sessions/{created['session_id']}")

    assert response.status_code == 200
    validate(instance=response.json(), schema=_response_schema(openapi))


async def test_get_unknown_session_returns_404(api_client: AsyncClient) -> None:
    response = await api_client.get("/v1/checkout-sessions/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


@pytest.mark.parametrize(
    "campo_proibido",
    [
        {"email": "cliente@example.com"},
        {"payment_method": "credit_card"},
        {"coupon": "DESCONTO10"},
    ],
)
async def test_rejects_fields_out_of_scope(api_client: AsyncClient, campo_proibido: dict) -> None:
    """FR-006, FR-007, FR-008: campos fora de escopo devem ser rejeitados, nao ignorados."""
    payload = {**VALID_PAYLOAD, **campo_proibido}

    response = await api_client.post("/v1/checkout-sessions", json=payload)

    assert response.status_code == 422


async def test_health_endpoint(api_client: AsyncClient) -> None:
    response = await api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
