"""OutboxRelayWorker (T020): publica eventos pendentes do outbox no Kafka.

Poll periodico sobre outbox_events. Apos exceder MAX_ATTEMPTS tentativas
falhas de publicacao, marca o registro como FALHOU e publica o payload
original no topico de DLQ, em vez de bloquear indefinidamente o
processamento dos demais registros pendentes (Principio III, NON-NEGOTIABLE
- ver data-model.md).
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.adapters.outbound.persistence.models import OutboxEventModel
from src.domain.ports import EventPublisher

TOPICO_CHECKOUT_EVENTOS = "checkout.eventos"
TOPICO_DLQ = "checkout.outbox.dlq"
MAX_ATTEMPTS = 5

logger = structlog.get_logger(__name__)


class OutboxRelayWorker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        publisher: EventPublisher,
        max_attempts: int = MAX_ATTEMPTS,
    ) -> None:
        self._session_factory = session_factory
        self._publisher = publisher
        self._max_attempts = max_attempts

    async def processar_pendentes(self) -> int:
        """Processa um lote de eventos PENDENTE. Retorna quantos foram publicados."""
        publicados = 0
        async with self._session_factory() as db_session:
            result = await db_session.execute(
                select(OutboxEventModel).where(OutboxEventModel.status == "PENDENTE")
            )
            pendentes = list(result.scalars())

            for evento in pendentes:
                try:
                    await self._publisher.publicar(
                        topico=TOPICO_CHECKOUT_EVENTOS,
                        chave=str(evento.event_id),
                        payload=json.dumps(evento.payload).encode(),
                    )
                    evento.status = "PUBLICADO"
                    evento.published_at = datetime.now(UTC)
                    publicados += 1
                except Exception:  # noqa: BLE001 - falha de publicacao e esperada e tratada aqui
                    evento.attempt_count += 1
                    logger.warning(
                        "outbox.publicacao_falhou",
                        event_id=str(evento.event_id),
                        attempt_count=evento.attempt_count,
                    )
                    if evento.attempt_count >= self._max_attempts:
                        evento.status = "FALHOU"
                        try:
                            await self._publisher.publicar(
                                topico=TOPICO_DLQ,
                                chave=str(evento.event_id),
                                payload=json.dumps(evento.payload).encode(),
                            )
                            logger.error(
                                "outbox.enviado_para_dlq",
                                event_id=str(evento.event_id),
                                attempt_count=evento.attempt_count,
                            )
                        except Exception:  # noqa: BLE001 - DLQ tambem pode estar indisponivel
                            logger.error(
                                "outbox.falha_ao_publicar_na_dlq",
                                event_id=str(evento.event_id),
                                attempt_count=evento.attempt_count,
                            )

            await db_session.commit()
        return publicados

    async def run_forever(self, poll_interval_seconds: float = 1.0) -> None:
        while True:
            await self.processar_pendentes()
            await asyncio.sleep(poll_interval_seconds)
