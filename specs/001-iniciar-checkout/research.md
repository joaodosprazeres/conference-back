# Research: Iniciar Checkout

Todas as incertezas do Technical Context foram resolvidas antes desta fase (decisões de
negócio confirmadas pelo usuário durante a especificação e o planejamento). Este documento
registra a decisão técnica, a razão e as alternativas descartadas para cada escolha —
inclusive as já dadas como restrição pela constituição, para que o histórico de
planejamento fique autocontido.

## Linguagem e versão

- **Decision**: Python 3.12
- **Rationale**: versão estável mais recente com suporte pleno a `typing` moderno
  (necessário para `mypy --strict`, Quality Gate da constituição), compatível com FastAPI,
  SQLAlchemy 2.x e `aiokafka`.
- **Alternatives considered**: Python 3.11 (também viável, mas 3.12 traz melhorias de
  performance em `asyncio` relevantes para um serviço I/O-bound); nenhuma outra linguagem
  foi considerada — Python é fixado pela constituição.

## Framework de API síncrona

- **Decision**: FastAPI, como adapter de entrada (inbound) na arquitetura hexagonal
- **Rationale**: fixado pela constituição; gera OpenAPI automaticamente a partir dos
  schemas Pydantic, satisfazendo o Princípio VII (Contrato de API Estável) sem trabalho
  manual de documentação.
- **Alternatives considered**: nenhuma — escolha de stack já decidida no nível do projeto.

## Persistência

- **Decision**: SQLAlchemy 2.x (estilo assíncrono) sobre PostgreSQL, com driver `asyncpg`
- **Rationale**: SQLAlchemy é fixado pela constituição; PostgreSQL é o par natural para
  garantir a transação atômica exigida pelo outbox pattern (Princípio III) — sessão de
  checkout e evento de outbox gravados na mesma transação ACID.
- **Alternatives considered**: driver síncrono `psycopg2` — descartado porque o serviço é
  I/O-bound e se beneficia de um stack assíncrono ponta a ponta (FastAPI async + SQLAlchemy
  async).

## Publicação de evento e outbox

- **Decision**: Transactional Outbox com relay por polling: um processo separado lê a
  tabela `outbox_events` (status pendente) e publica no Kafka via `aiokafka`, marcando o
  registro como publicado após confirmação do broker.
- **Rationale**: satisfaz o piso NON-NEGOTIABLE do Princípio III sem exigir infraestrutura
  de CDC (ex.: Debezium), mantendo a solução simples e sob controle total da aplicação
  nesta fase inicial do projeto.
- **Alternatives considered**: CDC via Debezium — mais robusto a longo prazo (menor
  latência de publicação, sem polling), mas adiciona uma peça de infraestrutura extra
  desnecessária para o volume desta primeira feature. Pode ser revisitado depois sem
  mudança no contrato do evento nem no domínio (troca de adapter de mensageria).

## Idempotência e DLQ do lado consumidor

- **Decision**: o requisito de "consumidor idempotente" e "DLQ" do Princípio III aplica-se
  a quem consome `CheckoutIniciado`. Nesta feature, nenhum serviço consome esse evento — o
  módulo de carrinho verifica o congelamento consultando o status da sessão via API, não
  reagindo ao evento.
- **Rationale**: o evento é publicado por razões de rastreabilidade/analytics (Princípio V)
  desde já, mesmo sem consumidor imediato; isso evita reescrever o produtor quando um
  consumidor real for adicionado.
- **Alternatives considered**: não publicar evento nenhum nesta feature — descartado por
  decisão explícita do usuário, para já estabelecer o padrão de emissão com `saga_id` desde
  o primeiro passo da saga.
- **Follow-up**: quando um consumidor real for implementado (ex.: analytics, ou o próprio
  carrinho passar a reagir por evento no futuro), a idempotência e a DLQ desse consumidor
  específico tornam-se um gate obrigatório de PR daquela feature.

## Contrato do evento

- **Decision**: `CheckoutIniciado` modelado como modelo Pydantic versionado em
  `libs/contracts/src/contracts/events/checkout_iniciado.py`.
- **Rationale**: aplica o Princípio IV; monorepo elimina o custo de coordenação de deploy
  entre repositórios que uma lib compartilhada teria em multi-repo.
- **Alternatives considered**: JSON Schema + Schema Registry — mais robusto para consumidores
  fora do monorepo/fora de Python, mas adiciona infraestrutura (o próprio Schema Registry)
  desnecessária enquanto todos os consumidores previstos estão no mesmo monorepo Python.

## Rastreabilidade e observabilidade

- **Decision**: OpenTelemetry SDK para tracing distribuído; `structlog` para logging
  estruturado em JSON; ambos carregando `saga_id` como atributo/campo obrigatório.
- **Rationale**: aplica o Princípio V (Correlation ID + Tracing) e o Princípio VIII
  (Observabilidade); OpenTelemetry é o padrão de fato para tracing poliglota, relevante
  porque outros serviços do monorepo poderão ser implementados em stacks diferentes no
  futuro.
- **Alternatives considered**: logging não estruturado com correlação manual — descartado
  por não escalar para depuração entre serviços assíncronos.

## Testes e qualidade

- **Decision**: `pytest` + `pytest-asyncio` para testes unitários e de integração;
  `pytest-cov` com gate de 80%; `mypy --strict`; `ruff` para lint/format; teste de contrato
  dedicado validando o payload publicado contra o modelo em `libs/contracts` e a resposta da
  API contra o schema OpenAPI.
- **Rationale**: decisões já fixadas nos Quality Gates de Engenharia da constituição.
- **Alternatives considered**: nenhuma — não há liberdade de escolha aqui, é regra do
  projeto.

## Regras de negócio confirmadas (não technical, mas fixadas antes do design)

- **Prazo de expiração**: 15 minutos, fixo nesta versão (sem configuração dinâmica por
  enquanto).
- **Congelamento do carrinho**: checkout apenas expõe o status da sessão para consulta; a
  lógica de bloqueio de edição vive inteiramente no módulo de carrinho (fora do escopo de
  código desta feature).
