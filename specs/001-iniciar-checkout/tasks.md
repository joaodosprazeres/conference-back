---

description: "Task list template for feature implementation"
---

# Tasks: Iniciar Checkout

**Input**: Design documents from `/specs/001-iniciar-checkout/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Incluídos. Não são opcionais neste projeto — a constituição (Quality Gates de
Engenharia) exige cobertura mínima de 80%, teste de contrato obrigatório por evento Kafka e
por endpoint, como gate bloqueante de PR.

**Organization**: Existe uma única user story nesta feature (P1 — MVP), conforme spec.md.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: A qual user story a tarefa pertence (US1)
- Caminhos de arquivo exatos em cada descrição

## Path Conventions

Monorepo multi-pacote (ver plan.md — Project Structure):
- `services/checkout/src/` e `services/checkout/tests/` — único serviço implementado nesta fase
- `libs/contracts/src/` — pacote compartilhado de contratos de evento

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: inicialização do projeto e estrutura básica

- [X] T001 Criar o esqueleto de diretórios do monorepo: `services/checkout/src/{domain,adapters/inbound/api,adapters/outbound/persistence,adapters/outbound/messaging,adapters/observability}`, `services/checkout/tests/{unit,contract,integration}` e `libs/contracts/src/contracts/events`, conforme plan.md — Project Structure
- [X] T002 [P] Inicializar o pacote `libs/contracts` com `libs/contracts/pyproject.toml` (pacote Python instalável, Pydantic v2 como dependência)
- [X] T003 Inicializar `services/checkout/pyproject.toml` com Python 3.12 e dependências: FastAPI, Pydantic v2, SQLAlchemy 2.x + `asyncpg`, `aiokafka`, `opentelemetry-sdk`, `structlog`, `pytest`, `pytest-asyncio`, `pytest-cov`, `mypy`, `ruff`; incluir `libs/contracts` como dependência local; configurar `mypy --strict` e regras do `ruff` (depende de T001)
- [X] T004 [P] Criar `docker-compose.yml` na raiz do repositório com PostgreSQL e Kafka para desenvolvimento local e testes de integração (pré-requisito de quickstart.md)

**Checkpoint**: projeto inicializado, dependências resolvidas, infraestrutura local disponível

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: infraestrutura central que precisa existir antes de qualquer user story

**⚠️ CRITICAL**: nenhuma tarefa de user story pode começar antes desta fase estar completa

- [X] T005 Criar as entidades de domínio `CheckoutSession` e o value object `CartItemSnapshot`, com as invariantes de data-model.md (itens não vazios, quantidade > 0, preço unitário ≥ 0, cálculo de `total`, status `INICIADO`/`EXPIRADO` derivado de `expires_at`), em `services/checkout/src/domain/entities.py` (depende de T003)
- [X] T006 [P] Definir as portas `CheckoutSessionRepository` e `EventPublisher` (interfaces, Princípio I — sem import de framework) em `services/checkout/src/domain/ports.py` (depende de T003)
- [X] T007 [P] Criar o modelo Pydantic versionado do evento `CheckoutIniciado` (v1.0), conforme `contracts/events/checkout-iniciado.schema.json`, em `libs/contracts/src/contracts/events/checkout_iniciado.py` (depende de T002)
- [X] T008 Criar os modelos SQLAlchemy e a migração inicial para as tabelas `checkout_sessions` e `outbox_events` — incluindo em `outbox_events` os campos `status` (`PENDENTE`/`PUBLICADO`/`FALHOU`) e `attempt_count` (data-model.md) — em `services/checkout/src/adapters/outbound/persistence/models.py` e `services/checkout/src/adapters/outbound/persistence/migrations/` (depende de T003)
- [X] T009 [P] Configurar logging estruturado em JSON (`structlog`) incluindo o campo `saga_id` obrigatório em todo log, em `services/checkout/src/adapters/observability/logging.py` (Princípio V) (depende de T003)
- [X] T010 [P] Configurar tracing distribuído (OpenTelemetry SDK), propagando `saga_id` como atributo de span, em `services/checkout/src/adapters/observability/tracing.py` (Princípio V) (depende de T003)
- [X] T011 Criar o app FastAPI (composition root) com wiring inicial e o endpoint `GET /health` em `services/checkout/src/main.py` (Princípio VIII) (depende de T003)

**Checkpoint**: fundação pronta — a implementação da User Story 1 pode começar

---

## Phase 3: User Story 1 - Iniciar checkout a partir do carrinho (Priority: P1) 🎯 MVP

**Goal**: cliente convidado envia o carrinho (id + itens) e recebe de volta o id da sessão de
checkout criada, o total calculado e o prazo de expiração; o carrinho permanece consultável
quanto ao status da sessão até ela expirar.

**Independent Test**: enviar um carrinho válido para o início do checkout e verificar que uma
sessão é criada com total correto e prazo de expiração — sem depender de payment, order,
inventory ou cart estarem implementados (spec.md — Independent Test).

### Tests for User Story 1 ⚠️

> Escrever estes testes PRIMEIRO; garantir que falham antes de implementar (Quality Gates de
> Engenharia da constituição exigem cobertura ≥ 80% e teste de contrato obrigatório).

- [X] T012 [P] [US1] Teste de contrato da API: valida `POST /v1/checkout-sessions` e
      `GET /v1/checkout-sessions/{id}` contra `contracts/openapi.yaml`, incluindo o caso de
      rejeição de campos não previstos (`email`, `payment_method`, `coupon` — FR-006/007/008)
      e um teste simples de `GET /health`, em
      `services/checkout/tests/contract/test_checkout_sessions_api_contract.py`
- [X] T013 [P] [US1] Teste de contrato do evento: valida o payload publicado contra
      `libs/contracts` / `contracts/events/checkout-iniciado.schema.json` em
      `services/checkout/tests/contract/test_checkout_iniciado_event_contract.py`
- [X] T014 [P] [US1] Testes unitários das invariantes de `CheckoutSession` (itens não vazios,
      quantidade/preço inválidos, cálculo de total, status derivado por `expires_at`) em
      `services/checkout/tests/unit/test_checkout_session.py`
- [X] T015 [P] [US1] Teste de integração — Acceptance Scenarios 1 e 2 (criação da sessão,
      total correto com múltiplos itens) em
      `services/checkout/tests/integration/test_iniciar_checkout.py`
- [X] T016 [P] [US1] Teste de integração — Acceptance Scenario 4 (status muda para `EXPIRADO`
      na consulta após `expires_at`, sem job de background) em
      `services/checkout/tests/integration/test_checkout_expiration.py`

### Implementation for User Story 1

- [X] T017 [US1] Implementar o caso de uso `IniciarCheckout` (calcula total, monta
      `CheckoutSession`, gera `saga_id`) em `services/checkout/src/domain/use_cases.py`
      (depende de T005, T006)
- [X] T018 [US1] Implementar o adapter `SqlAlchemyCheckoutSessionRepository`, persistindo
      `CheckoutSession` e o `OutboxEvent` correspondente na mesma transação (Princípio III —
      outbox transacional), em
      `services/checkout/src/adapters/outbound/persistence/repository.py` (depende de T006,
      T008)
- [X] T019 [P] [US1] Implementar o adapter `KafkaEventPublisher` (via `aiokafka`),
      implementando a porta `EventPublisher`, em
      `services/checkout/src/adapters/outbound/messaging/kafka_publisher.py` (depende de T006)
- [X] T020 [US1] Implementar o `OutboxRelayWorker`: consulta `outbox_events` pendentes,
      publica via `EventPublisher`, marca como publicado; após exceder `max_attempts`
      tentativas falhas, marca o registro como `FALHOU` e publica o payload original no
      tópico de DLQ `checkout.outbox.dlq` (Princípio III — DLQ do lado do produtor), em
      `services/checkout/src/adapters/outbound/messaging/outbox_relay.py` (depende de T008,
      T019)
- [X] T021 [P] [US1] Implementar os schemas Pydantic de request/response
      (`IniciarCheckoutRequest`, `CheckoutSessionResponse`) conforme
      `contracts/openapi.yaml`, com `model_config = ConfigDict(extra="forbid")` em
      `IniciarCheckoutRequest` para rejeitar campos não previstos (FR-006/007/008), em
      `services/checkout/src/adapters/inbound/api/schemas.py` (depende de T007)
- [X] T022 [US1] Implementar o router FastAPI com `POST /v1/checkout-sessions` e
      `GET /v1/checkout-sessions/{session_id}`, conectando ao caso de uso e ao repositório,
      propagando `saga_id` em log/trace, em
      `services/checkout/src/adapters/inbound/api/routers.py` (depende de T017, T018, T021,
      T009, T010)
- [X] T023 [US1] Registrar o router e iniciar o `OutboxRelayWorker` junto ao ciclo de vida do
      app FastAPI em `services/checkout/src/main.py` (depende de T020, T022, T011)
- [X] T024 [US1] Instrumentar métrica de latência dos endpoints de checkout session
      (Princípio VIII) em `services/checkout/src/adapters/inbound/api/routers.py` (depende de
      T022, T010)
- [X] T025 [P] [US1] Teste de integração verificando que uma falha persistente de publicação
      no `OutboxRelayWorker` resulta em `status=FALHOU` e uma mensagem no tópico
      `checkout.outbox.dlq` (Princípio III) em
      `services/checkout/tests/integration/test_outbox_dlq.py` (depende de T020)
- [X] T026 [US1] Teste de integração verificando que `POST /v1/checkout-sessions` responde em
      até 2 segundos (SC-001) em
      `services/checkout/tests/integration/test_iniciar_checkout.py` (depende de T022, T024)

**Checkpoint**: User Story 1 completa e testável de forma independente — MVP pronto

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: itens que cruzam a feature inteira, não específicos de uma user story

- [X] T027 [P] Criar `services/checkout/Dockerfile`, conforme a seção "Build e Deployment" da
      constituição
- [X] T028 [P] Escrever `services/checkout/README.md` com instruções para rodar localmente
      (docker-compose, `uvicorn`), referenciando quickstart.md
- [X] T029 Executar manualmente os 4 cenários de quickstart.md ponta a ponta e registrar o
      resultado
- [X] T030 [P] Verificar que `mypy --strict`, `ruff check` e `pytest --cov` (≥ 80%) passam sem
      erro em `services/checkout` (Quality Gates de Engenharia)
- [X] T031 [P] Registrar a versão `1.0` do evento `CheckoutIniciado` no changelog/versionamento
      de `libs/contracts` (Princípio IV)

---

## Escopo e Limites

Nenhuma tarefa desta lista implementa o bloqueio de edição do carrinho em si (FR-010), nem a
liberação do carrinho após expiração (parte de FR-011), nem SC-003 diretamente. Por decisão
de design (research.md, plan.md), o checkout apenas **expõe** o status da sessão via
`GET /v1/checkout-sessions/{session_id}` (T022); é o módulo de **carrinho** — fora do escopo
de código desta feature e ainda não implementado — quem consulta esse status e decide
bloquear ou liberar a edição. FR-010, a parte de FR-011 sobre liberar o carrinho, e SC-003
só terão cobertura de tarefas quando o serviço de carrinho for especificado e planejado.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — pode começar imediatamente
- **Foundational (Phase 2)**: depende da conclusão do Setup — BLOQUEIA a User Story 1
- **User Story 1 (Phase 3)**: depende da conclusão da Foundational
- **Polish (Phase 4)**: depende da conclusão da User Story 1

### Dentro da User Story 1

- Testes (T012–T016) devem ser escritos e falhar antes da implementação (T017–T024)
- Casos de uso e portas (T017) antes dos adapters que os implementam (T018, T019)
- Repositório e publisher (T018, T019) antes do relay e do router (T020, T022)
- Router e relay (T022, T020) antes do wiring final no app (T023)
- T025 (teste de DLQ) e T026 (teste de latência SC-001) validam comportamento de T020/T022/T024
  já implementado — rodam por último dentro da User Story 1

### Parallel Opportunities

- T002 e T004 podem rodar em paralelo com T003 (arquivos diferentes)
- T006, T007, T009, T010 podem rodar em paralelo entre si na Fase 2 (arquivos diferentes)
- Todos os testes de US1 (T012–T016) podem rodar em paralelo entre si
- T019 e T021 podem rodar em paralelo com T018 (arquivos diferentes, mesma dependência T006/T007)
- T027, T028, T030, T031 podem rodar em paralelo na Fase de Polish

---

## Parallel Example: User Story 1

```bash
# Testes de User Story 1, todos em paralelo:
Task: "Teste de contrato da API em services/checkout/tests/contract/test_checkout_sessions_api_contract.py"
Task: "Teste de contrato do evento em services/checkout/tests/contract/test_checkout_iniciado_event_contract.py"
Task: "Testes unitários de CheckoutSession em services/checkout/tests/unit/test_checkout_session.py"
Task: "Teste de integração de criação de sessão em services/checkout/tests/integration/test_iniciar_checkout.py"
Task: "Teste de integração de expiração em services/checkout/tests/integration/test_checkout_expiration.py"

# Adapters independentes da User Story 1, em paralelo:
Task: "KafkaEventPublisher em services/checkout/src/adapters/outbound/messaging/kafka_publisher.py"
Task: "Schemas de request/response em services/checkout/src/adapters/inbound/api/schemas.py"
```

---

## Implementation Strategy

### MVP First (única user story desta feature)

1. Completar Fase 1: Setup
2. Completar Fase 2: Foundational (CRÍTICO — bloqueia a User Story 1)
3. Completar Fase 3: User Story 1
4. **PARAR E VALIDAR**: rodar quickstart.md e confirmar os Quality Gates (T029, T030)
5. Completar Fase 4: Polish (Dockerfile, README, versionamento de contrato)

Como há uma única user story nesta feature, o MVP e a entrega completa coincidem — não há
fatiamento adicional de escopo a decidir aqui.

---

## Notes

- `[P]` = arquivos diferentes, sem dependência entre si
- `[US1]` mapeia a tarefa à única user story desta feature, para rastreabilidade
- Verificar que os testes falham antes de implementar
- Fazer commit após cada tarefa ou grupo lógico de tarefas
- Parar no checkpoint da Fase 3 para validar a User Story 1 de forma independente antes de
  seguir para a Fase 4
