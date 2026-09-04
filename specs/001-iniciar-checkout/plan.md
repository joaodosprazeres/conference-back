# Implementation Plan: Iniciar Checkout

**Branch**: `001-iniciar-checkout` | **Date**: 2026-09-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-iniciar-checkout/spec.md`

## Summary

Permitir que um cliente convidado inicie uma sessão de checkout a partir do seu carrinho:
o checkout recebe (via endpoint REST síncrono) o id do carrinho e o snapshot de itens
(produto, quantidade, preço unitário), cria uma sessão em estado `INICIADO` com total
calculado e prazo de expiração de 15 minutos, grava essa criação e o evento informativo
`CheckoutIniciado` na mesma transação (outbox), e retorna id da sessão, total e prazo ao
chamador. O congelamento do carrinho de origem é responsabilidade do módulo de carrinho,
que consulta o status da sessão exposto pelo checkout — esta feature não implementa o lado
do carrinho. Abordagem técnica: arquitetura hexagonal em Python/FastAPI/SQLAlchemy sobre
PostgreSQL, publicação assíncrona via outbox relay para Kafka, contrato do evento modelado
no pacote compartilhado `libs/contracts`.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI (adapter de entrada HTTP), Pydantic v2 (modelos e
contratos), SQLAlchemy 2.x + driver assíncrono `asyncpg` (adapter de persistência),
`aiokafka` (adapter de mensageria/outbox relay), OpenTelemetry SDK (tracing), `structlog`
(logging estruturado em JSON)

**Storage**: PostgreSQL — tabela `checkout_sessions` (estado da sessão) e tabela `outbox_events`
(transactional outbox) no schema do serviço checkout

**Testing**: `pytest` + `pytest-asyncio` (unitário e integração), testes de contrato do
evento contra `libs/contracts` e do endpoint contra o OpenAPI publicado, `pytest-cov`
(gate de 80%), `mypy --strict`, `ruff`

**Target Platform**: Linux container (Docker), orquestrado via Kubernetes (branch de
release dedicada `release/checkout`, conforme a constituição)

**Project Type**: web-service — um dos 5 microsserviços do monorepo `conference-back`;
único com implementação real nesta fase

**Performance Goals**: sem SLO numérico fixo em produção (Constituição, Princípio VIII);
meta de UX desta feature (spec SC-001): resposta ao chamador em até 2s. Publicação do
evento no Kafka é assíncrona via outbox relay e não bloqueia a resposta síncrona.

**Constraints**: entrega at-least-once com outbox transacional (Princípio III,
NON-NEGOTIABLE); domínio isolado de framework (Princípio I, NON-NEGOTIABLE); `saga_id`
obrigatório em toda chamada e evento (Princípio V); nenhum dado sensível envolvido nesta
feature (Princípio VI — não aplicável diretamente, sem dado de pagamento aqui)

**Scale/Scope**: uma única capacidade (iniciar sessão de checkout); os outros 4
microsserviços do domínio (cart, payment, order, inventory) não existem ainda como
implementação — não fazem parte do escopo de código desta feature

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação | Status |
|---|---|---|
| I. Arquitetura Hexagonal (NON-NEGOTIABLE) | Domínio (`CheckoutSession`, caso de uso `IniciarCheckout`) não importa FastAPI/SQLAlchemy/Kafka; entram via portas `CheckoutSessionRepository` e `EventPublisher`, implementadas em adapters | PASS |
| II. Checkout Orquestrador de Saga | Esta feature implementa apenas o primeiro estado da máquina (`INICIADO`/`EXPIRADO`); não há ainda comando a payment/order/inventory — consistente com o escopo do spec, não é violação, é implementação incremental do princípio | PASS (parcial, por escopo) |
| III. Outbox + Idempotência + DLQ (NON-NEGOTIABLE) | Publicação do evento `CheckoutIniciado` usa outbox transacional (grava sessão + evento na mesma transação). Idempotência de consumidor e DLQ são requisitos que se aplicam a quem consumir o evento; nenhum consumidor existe ainda (o carrinho consulta status, não consome evento) — documentado em research.md, não é uma exceção ao princípio, é ausência de consumidor no momento | PASS |
| IV. Contratos via Pacote Compartilhado | Evento `CheckoutIniciado` modelado como novo modelo Pydantic em `libs/contracts`, versionado | PASS |
| V. Rastreabilidade de Saga | `saga_id` gerado na criação da sessão, presente no evento e em todo log/trace da requisição | PASS |
| VI. Segurança/LGPD | Nenhum dado de cartão/CPF é recebido ou processado nesta feature | PASS (não aplicável) |
| VII. Contrato de API Estável | Endpoint exposto em `/v1/checkout-sessions`, documentado via OpenAPI gerado pelo FastAPI | PASS |
| VIII. Observabilidade e Performance | Métrica de latência do endpoint e health check (`/health`) fazem parte do Definition of Done desta feature | PASS |

Nenhuma violação identificada. **Complexity Tracking não se aplica** — não há desvio de
princípio a justificar.

**Re-check pós-Fase 1**: o desenho de dados (data-model.md), os contratos (contracts/) e o
guia de validação (quickstart.md) não introduziram nenhuma dependência de domínio em
framework, nenhum evento fora do pacote compartilhado, nem qualquer dado sensível — todas as
linhas da tabela acima permanecem PASS após o design detalhado.

## Project Structure

### Documentation (this feature)

```text
specs/001-iniciar-checkout/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
services/
├── checkout/                          # único serviço com implementação real nesta fase
│   ├── src/
│   │   ├── domain/                    # entidades, portas e casos de uso — sem dependência de framework
│   │   │   ├── entities.py            # CheckoutSession, CartItemSnapshot
│   │   │   ├── ports.py               # CheckoutSessionRepository, EventPublisher (interfaces)
│   │   │   └── use_cases.py           # IniciarCheckout
│   │   ├── adapters/
│   │   │   ├── inbound/api/           # FastAPI: routers, schemas de request/response, versionamento /v1
│   │   │   ├── outbound/persistence/  # SQLAlchemy: models, repository concreto, migrações
│   │   │   └── outbound/messaging/    # aiokafka producer, outbox relay (poller)
│   │   └── main.py                    # composition root / wiring
│   ├── tests/
│   │   ├── unit/                      # domínio isolado, sem I/O
│   │   ├── contract/                  # valida payload do evento contra libs/contracts e API contra OpenAPI
│   │   └── integration/               # API + Postgres + outbox relay (containers)
│   ├── Dockerfile                     # services/checkout/Dockerfile (Constituição, Build e Deployment)
│   └── pyproject.toml
├── cart/                              # ainda não implementado (fora do escopo desta feature)
├── payment/                           # ainda não implementado
├── order/                             # ainda não implementado
└── inventory/                         # ainda não implementado

libs/
└── contracts/                         # pacote interno compartilhado (Princípio IV)
    ├── src/contracts/events/
    │   └── checkout_iniciado.py       # modelo Pydantic versionado do evento
    └── pyproject.toml
```

**Structure Decision**: monorepo multi-pacote — um diretório `services/<nome>` por
microsserviço (bounded context) mais `libs/contracts` como pacote compartilhado de eventos.
Nenhuma das opções padrão do template (single project / web app frontend+backend / mobile+API)
se aplica diretamente; a estrutura acima é a adotada, com apenas `services/checkout`
contendo código real nesta fase — os demais diretórios de serviço serão criados quando cada
um for implementado, conforme "Escopo do Monorepo e Estratégia de Mocks" na constituição.

## Complexity Tracking

*Não se aplica — nenhuma violação de princípio identificada no Constitution Check.*
