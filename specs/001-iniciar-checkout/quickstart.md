# Quickstart: Validar "Iniciar Checkout"

Guia para provar que a feature funciona ponta a ponta. Não contém código de implementação —
apenas os passos de execução e o resultado esperado. Referências: [data-model.md](./data-model.md),
[contracts/openapi.yaml](./contracts/openapi.yaml), [contracts/events/checkout-iniciado.schema.json](./contracts/events/checkout-iniciado.schema.json).

## Pré-requisitos

A partir da raiz do monorepo, subir tudo com Docker Compose (Postgres, Kafka e o próprio
serviço checkout — a migração do banco roda automaticamente antes do servidor subir):

```bash
docker compose up -d --build
```

(Alternativa para desenvolvimento com hot-reload: `docker compose up -d postgres kafka` e
rodar o serviço localmente com `uv run uvicorn` — ver a seção "Opção B" em
[services/checkout/README.md](../../services/checkout/README.md).)

Isso deixa disponível:

- API do checkout em `http://localhost:8000/v1`, conforme `contracts/openapi.yaml`.
- PostgreSQL com o schema do serviço `checkout` já migrado.
- Kafka acessível do host em `localhost:9094` (listener externo — ver comentário no
  `docker-compose.yml` sobre por que há dois listeners) e do próprio container em
  `kafka:9092`.

Para observar o evento `CheckoutIniciado` publicado, um consumidor simples como `kcat`
funciona sem configuração extra (o tópico é criado automaticamente no primeiro publish):

```bash
kcat -b localhost:9094 -t checkout.eventos -C
```

## Cenário 1 — Iniciar checkout com sucesso (Acceptance Scenario 1 e 2 do spec)

1. Enviar `POST /v1/checkout-sessions` com um `cart_id` e uma lista de itens (quantidade e
   preço unitário variados), conforme `IniciarCheckoutRequest` no OpenAPI.
2. **Esperado**: resposta `201` com `session_id`, `status: "INICIADO"`, `total` igual à soma
   de `quantity × unit_price` de todos os itens enviados, e `expires_at` 15 minutos à frente
   do momento da chamada.
3. Consultar `GET /v1/checkout-sessions/{session_id}`.
4. **Esperado**: mesmo `total` e `expires_at` da criação; `status: "INICIADO"`.
5. Observar o tópico `checkout.eventos` (comando `kcat` nos Pré-requisitos acima).
6. **Esperado**: uma mensagem `CheckoutIniciado` (schema em
   `contracts/events/checkout-iniciado.schema.json`) com `session_id` e `saga_id` iguais ao
   retornado na criação, e `total`/`expires_at` coerentes com a resposta HTTP.

## Cenário 2 — Sessão expira e status muda na consulta (Acceptance Scenario 4)

1. Repetir o passo 1 do Cenário 1.
2. Aguardar (ou avançar o relógio do ambiente de teste) até após `expires_at`.
3. Consultar `GET /v1/checkout-sessions/{session_id}` novamente.
4. **Esperado**: `status: "EXPIRADO"` — sem exigir nenhum job de background rodando entre a
   criação e a consulta (o status é derivado na leitura, ver data-model.md).

## Cenário 3 — Total correto com múltiplos itens (Acceptance Scenario 2)

1. Enviar `POST /v1/checkout-sessions` com ao menos dois itens de `quantity` e `unit_price`
   diferentes.
2. **Esperado**: `total` retornado é exatamente a soma de `quantity × unit_price` de cada
   item, sem qualquer desconto ou taxa aplicada (FR-008).

## Cenário 4 — Ausência de dados fora de escopo (FR-006, FR-007, FR-008, FR-009)

1. Repetir o passo 1 do Cenário 1 sem enviar e-mail, endereço, método de pagamento ou cupom
   (o schema `IniciarCheckoutRequest` nem permite esses campos).
2. **Esperado**: `201` normalmente — a ausência desses dados não é um erro nesta feature.
3. Verificar que nenhuma chamada foi feita aos (ainda inexistentes) serviços de payment,
   order ou inventory — nesta fase, isso é garantido pela ausência total de adapters para
   esses serviços no código do checkout (constituição — Escopo do Monorepo e Estratégia de
   Mocks).

## Verificação de Quality Gates (antes de considerar a feature pronta)

Rodar a partir de `services/checkout/` (ver
[README.md](../../services/checkout/README.md#quality-gates) para o setup completo com `uv`):

- `uv run pytest --cov` reportando cobertura ≥ 80% sobre o código da feature.
- `uv run mypy --strict src` sem erros nos módulos tocados.
- `uv run ruff check .` sem violações.
- Teste de contrato validando o payload publicado no Kafka contra
  `contracts/events/checkout-iniciado.schema.json` / o modelo em `libs/contracts`.
- Métrica de latência do endpoint e `GET /health` respondendo (Princípio VIII).
