# Checkout Service

Servico de checkout do monorepo `conference-back` — orquestrador da saga de compra
(ver [constitution.md](../../.specify/memory/constitution.md)). Esta versao implementa
apenas a feature [001-iniciar-checkout](../../specs/001-iniciar-checkout/spec.md).

## Rodando localmente

Pré-requisitos: Docker, Docker Compose, Python 3.12, [uv](https://docs.astral.sh/uv/)
(gerenciador de pacotes e ambientes deste monorepo — não usamos `pip` diretamente).

### Opção A — tudo em containers (mais simples)

A partir da raiz do monorepo, sobe Postgres, Kafka e o próprio serviço checkout
(migração roda automaticamente antes do servidor subir — ver `Dockerfile`):

```bash
docker compose up -d --build
```

Testar manualmente os cenários em
[quickstart.md](../../specs/001-iniciar-checkout/quickstart.md), por exemplo:

```bash
curl -X POST http://localhost:8000/v1/checkout-sessions \
  -H "Content-Type: application/json" \
  -d '{"cart_id": "cart-1", "items": [{"product_id": "sku-1", "quantity": 2, "unit_price": 10.0}]}'
```

### Opção B — infraestrutura em container, app local (loop de dev mais rápido)

Útil para hot-reload sem rebuild de imagem. Só sobe Postgres e Kafka:

```bash
docker compose up -d postgres kafka
```

Instalar as dependências, a partir da **raiz do monorepo** (workspace uv — resolve
`services/checkout` e a dependência local `libs/contracts` juntos):

```bash
uv sync --package checkout
```

Aplicar as migrações do banco e rodar o serviço (a partir de `services/checkout/`).
Fora de um container, o Kafka é alcançado pelo listener externo (porta `9094`
publicada no host — ver comentário no `docker-compose.yml`):

```bash
cd services/checkout
uv run alembic upgrade head
KAFKA_BOOTSTRAP_SERVERS=localhost:9094 uv run uvicorn src.main:app --reload --port 8000
```

## Rodando os testes

```bash
cd services/checkout
uv run pytest
```

A suíte cobre testes unitários (domínio, sem I/O), de contrato (API contra
`contracts/openapi.yaml`, evento contra `contracts/events/checkout-iniciado.schema.json`)
e de integração (requerem apenas PostgreSQL — `docker compose up -d postgres` — pois usam
um publisher de Kafka em memória; são pulados automaticamente se o banco não estiver
acessível).

## Quality Gates

```bash
cd services/checkout
uv run mypy --strict src
uv run ruff check .
uv run pytest --cov=src --cov-report=term-missing
```

A cobertura mínima exigida é 80% (Quality Gates de Engenharia da constituição).

## Atualizando dependências

```bash
# a partir da raiz do monorepo
uv add <pacote> --package checkout          # dependência de runtime
uv add <pacote> --package checkout --dev    # dependência de desenvolvimento
uv lock                                     # regenera uv.lock do workspace inteiro
```

## Arquitetura

Hexagonal (ports & adapters) — ver [plan.md](../../specs/001-iniciar-checkout/plan.md):

- `src/domain/` — entidades, portas e casos de uso, sem dependência de framework
- `src/adapters/inbound/api/` — FastAPI
- `src/adapters/outbound/persistence/` — SQLAlchemy + PostgreSQL
- `src/adapters/outbound/messaging/` — aiokafka + outbox relay
- `src/adapters/observability/` — logging estruturado, tracing e métricas
