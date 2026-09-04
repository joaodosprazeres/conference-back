"""Adapter de publicacao Kafka via aiokafka (T019), implementando a porta
EventPublisher. Inclui tambem um FakeEventPublisher em memoria, usado pelos
testes (nao depende de um broker real)."""

from __future__ import annotations

import os

from aiokafka import AIOKafkaProducer


class KafkaEventPublisher:
    def __init__(self, bootstrap_servers: str | None = None) -> None:
        self._bootstrap_servers = bootstrap_servers or os.environ.get(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(bootstrap_servers=self._bootstrap_servers)
        await self._producer.start()

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()

    async def publicar(self, topico: str, chave: str, payload: bytes) -> None:
        if self._producer is None:
            raise RuntimeError("KafkaEventPublisher nao foi iniciado (chamar start() primeiro)")
        await self._producer.send_and_wait(topico, value=payload, key=chave.encode())


class FakeEventPublisher:
    """Publisher em memoria para testes - nao requer um broker Kafka real.

    `falhar_topicos` permite simular indisponibilidade seletiva (ex.: o topico
    principal fora do ar, mas a DLQ acessivel) para testar o relay de outbox.
    """

    def __init__(self, falhar_topicos: set[str] | None = None) -> None:
        self.mensagens: list[tuple[str, str, bytes]] = []
        self._falhar_topicos = falhar_topicos or set()

    async def publicar(self, topico: str, chave: str, payload: bytes) -> None:
        if topico in self._falhar_topicos:
            raise ConnectionError(f"falha simulada de publicacao no topico {topico}")
        self.mensagens.append((topico, chave, payload))
