"""Router FastAPI da feature Iniciar Checkout (T022, T024).

POST /v1/checkout-sessions e GET /v1/checkout-sessions/{session_id}, conforme
contracts/openapi.yaml. saga_id e propagado em log e trace (Principio V);
latencia e instrumentada via metrica e log (Principio VIII).
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from src.adapters.inbound.api.schemas import CheckoutSessionResponse, IniciarCheckoutRequest
from src.adapters.observability.logging import bind_saga_id, clear_saga_id, get_logger
from src.adapters.observability.metrics import checkout_sessions_latency_ms
from src.adapters.observability.tracing import get_tracer, start_span_with_saga_id
from src.domain.entities import CartItemSnapshot, CheckoutSession
from src.domain.use_cases import IniciarCheckout

router = APIRouter(prefix="/v1", tags=["checkout-sessions"])
logger = get_logger(__name__)
tracer = get_tracer("checkout.api")


def _para_resposta(session: CheckoutSession) -> CheckoutSessionResponse:
    momento = datetime.now(UTC)
    return CheckoutSessionResponse(
        session_id=session.session_id,
        cart_id=session.cart_id,
        status=session.status_em(momento).value,
        total=session.total,
        expires_at=session.expires_at,
    )


@router.post(
    "/checkout-sessions",
    response_model=CheckoutSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def iniciar_checkout(
    body: IniciarCheckoutRequest, request: Request
) -> CheckoutSessionResponse:
    inicio = time.perf_counter()
    use_case = IniciarCheckout(request.app.state.checkout_repository)

    items = tuple(
        CartItemSnapshot(
            product_id=item.product_id, quantity=item.quantity, unit_price=item.unit_price
        )
        for item in body.items
    )
    session = await use_case.executar(cart_id=body.cart_id, items=items)

    bind_saga_id(str(session.saga_id))
    try:
        with start_span_with_saga_id(tracer, "iniciar_checkout", str(session.saga_id)):
            duracao_ms = (time.perf_counter() - inicio) * 1000
            checkout_sessions_latency_ms.record(duracao_ms, {"endpoint": "iniciar_checkout"})
            logger.info(
                "checkout.iniciado",
                session_id=str(session.session_id),
                cart_id=session.cart_id,
                duracao_ms=round(duracao_ms, 2),
            )
    finally:
        clear_saga_id()

    return _para_resposta(session)


@router.get("/checkout-sessions/{session_id}", response_model=CheckoutSessionResponse)
async def consultar_sessao_checkout(session_id: UUID, request: Request) -> CheckoutSessionResponse:
    repository = request.app.state.checkout_repository
    session = await repository.buscar_por_id(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sessao nao encontrada")

    return _para_resposta(session)
