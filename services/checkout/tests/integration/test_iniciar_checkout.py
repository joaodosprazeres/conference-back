"""Teste de integracao - Acceptance Scenarios 1 e 2 do spec.md (T015), e
verificacao de SC-001 - resposta em ate 2s (T026, resolve E2 da analise)."""

from __future__ import annotations

import time

from httpx import AsyncClient


async def test_criar_sessao_com_um_item(api_client: AsyncClient) -> None:
    payload = {
        "cart_id": "cart-abc",
        "items": [{"product_id": "sku-1", "quantity": 2, "unit_price": 10.0}],
    }

    response = await api_client.post("/v1/checkout-sessions", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["cart_id"] == "cart-abc"
    assert body["status"] == "INICIADO"
    assert float(body["total"]) == 20.0
    assert "session_id" in body
    assert "expires_at" in body


async def test_total_correto_com_multiplos_itens_e_precos_diferentes(api_client: AsyncClient) -> None:
    payload = {
        "cart_id": "cart-xyz",
        "items": [
            {"product_id": "sku-1", "quantity": 2, "unit_price": 10.0},
            {"product_id": "sku-2", "quantity": 3, "unit_price": 1.5},
            {"product_id": "sku-3", "quantity": 1, "unit_price": 99.99},
        ],
    }

    response = await api_client.post("/v1/checkout-sessions", json=payload)

    assert response.status_code == 201
    assert float(response.json()["total"]) == 124.49


async def test_sessao_criada_e_consultavel_via_get(api_client: AsyncClient) -> None:
    payload = {
        "cart_id": "cart-consulta",
        "items": [{"product_id": "sku-1", "quantity": 1, "unit_price": 5.0}],
    }

    created = (await api_client.post("/v1/checkout-sessions", json=payload)).json()
    fetched = (await api_client.get(f"/v1/checkout-sessions/{created['session_id']}")).json()

    assert fetched["session_id"] == created["session_id"]
    assert fetched["total"] == created["total"]
    assert fetched["expires_at"] == created["expires_at"]
    assert fetched["status"] == "INICIADO"


async def test_resposta_em_ate_2_segundos(api_client: AsyncClient) -> None:
    """SC-001: cliente convidado recebe a confirmacao de inicio em ate 2 segundos."""
    payload = {
        "cart_id": "cart-latencia",
        "items": [{"product_id": "sku-1", "quantity": 1, "unit_price": 1.0}],
    }

    inicio = time.perf_counter()
    response = await api_client.post("/v1/checkout-sessions", json=payload)
    duracao = time.perf_counter() - inicio

    assert response.status_code == 201
    assert duracao <= 2.0
