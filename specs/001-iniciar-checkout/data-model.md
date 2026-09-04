# Data Model: Iniciar Checkout

## CheckoutSession

Representa um processo de compra em andamento, iniciado a partir de um carrinho (spec:
Key Entities). É a raiz de agregado deste serviço para esta feature.

| Campo | Tipo | Regras |
|---|---|---|
| `session_id` | UUID | Gerado na criação; identidade da sessão. Também usado como `saga_id` desta feature em diante (Princípio V) — um único identificador correlaciona toda a saga a partir deste ponto. |
| `cart_id` | string | Obrigatório; id do carrinho de origem, recebido na requisição. |
| `items` | lista de `CartItemSnapshot` | Obrigatório; não pode ser vazia (FR-001, invariante de domínio — ver nota abaixo). |
| `total` | decimal | Calculado como soma de `quantity × unit_price` de todos os itens (FR-003). Nunca recebido diretamente na requisição. |
| `status` | enum: `INICIADO` \| `EXPIRADO` | Ver "Máquina de Estados" abaixo. |
| `expires_at` | datetime | `created_at + 15 minutos` (fixo nesta versão — research.md). |
| `created_at` | datetime | Timestamp de criação da sessão. |

**Nota sobre validação de itens**: o spec assume que o módulo de carrinho só envia dados
estruturalmente válidos (Assumptions), mas o domínio ainda impõe suas próprias invariantes
na construção da entidade (lista não vazia, quantidade > 0, preço unitário ≥ 0) como
proteção defensiva padrão de um agregado — isso não é a "validação de negócio extra" que o
spec descartou (ex.: bloquear sessão duplicada), é integridade estrutural do próprio dado
que compõe o agregado.

## CartItemSnapshot (value object, embutido em CheckoutSession)

| Campo | Tipo | Regras |
|---|---|---|
| `product_id` | string | Obrigatório. |
| `quantity` | inteiro | > 0. |
| `unit_price` | decimal | ≥ 0. |

Não é uma entidade com identidade própria nem é persistido separadamente com vida própria —
é um snapshot imutável capturado no momento da criação da sessão (FR-012: não é
re-consultado no módulo de carrinho depois).

## Máquina de Estados

```text
INICIADO ──(expires_at atingido)──> EXPIRADO
```

- **Decision**: o estado `EXPIRADO` é **derivado**, não persistido por um job de background.
  O campo `status` gravado permanece `INICIADO`; toda leitura da sessão (ex.: a consulta que
  o módulo de carrinho faz) calcula o status efetivo comparando `now() > expires_at` no
  momento da resposta.
- **Rationale**: evita a necessidade de um processo agendado (scheduler/reaper) só para
  marcar sessões como expiradas, o que seria complexidade desnecessária para esta primeira
  feature — o efeito observável (carrinho volta a ser editável, FR-011) só depende do status
  *consultado*, nunca de uma transição de escrita disparada por tempo.
- **Alternatives considered**: job periódico que varre sessões vencidas e atualiza o campo —
  rejeitado por adicionar um componente operacional (agendamento, monitoramento de mais um
  processo) sem benefício funcional nesta fase; pode ser adotado depois sem mudar o contrato
  de leitura, caso surja necessidade de listar/filtrar sessões expiradas em massa.

Estados futuros (`ESTOQUE_RESERVADO`, `PAGO`, `CONFIRMADO`, caminhos de compensação —
Princípio II da constituição) pertencem à feature de confirmação do checkout, fora do
escopo desta especificação.

## OutboxEvent

Registro técnico de suporte ao Princípio III (Outbox + Idempotência + DLQ), não é uma
entidade de domínio — vive no adapter de persistência, não no domínio.

| Campo | Tipo | Regras |
|---|---|---|
| `event_id` | UUID | Identidade do registro de outbox. |
| `event_type` | string | `"CheckoutIniciado"` nesta feature. |
| `payload` | JSON | Serialização do evento conforme `libs/contracts` (ver `contracts/events/checkout-iniciado.schema.json`). |
| `status` | enum: `PENDENTE` \| `PUBLICADO` \| `FALHOU` | Controla o relay de publicação. `FALHOU` após exceder `max_attempts`. |
| `attempt_count` | inteiro | Incrementado a cada tentativa de publicação malsucedida. |
| `created_at` | datetime | Mesma transação da criação da `CheckoutSession`. |
| `published_at` | datetime \| null | Preenchido pelo relay após confirmação do broker. |

`CheckoutSession` e o `OutboxEvent` correspondente são gravados na mesma transação de banco
(transactional outbox) — nunca um sem o outro.

**DLQ do lado do produtor**: após exceder `max_attempts` tentativas de publicação (ex.: 5),
o relay marca o registro como `FALHOU` e publica o payload original em um tópico Kafka
dedicado de DLQ (ex.: `checkout.outbox.dlq`) para inspeção manual, em vez de bloquear
indefinidamente o processamento dos demais registros pendentes. Isso cumpre o requisito de
DLQ do Princípio III (NON-NEGOTIABLE) também no lado do produtor, complementando a
idempotência/DLQ do lado consumidor (ver research.md).
