<!--
Sync Impact Report
==================
Version change: 1.0.0 → 1.1.0
Modified principles: none — the 8 Core Principles and Quality Gates de Engenharia are unchanged
Added sections:
  - Build e Deployment (new Section 4): Dockerfile por serviço, branch de release dedicada por
    serviço com manifestos Kubernetes, promoção sob demanda (não sincronizada a cada commit)
Removed sections: none
Deferred TODOs: none
Templates requiring follow-up:
  - .specify/templates/plan-template.md — Project Structure / deployment sections of future
    plans should reflect the per-service Dockerfile location and release/<service> branch
    convention introduced here.

--------------------------------------------------------------------------------
Sync Impact Report (previous amendment, kept for history)
==========================================================
Version change: [template] → 1.0.0 (initial ratification)
Modified principles: n/a (first adoption; constitution.md previously held only unfilled placeholders)
Added sections:
  - Core Principles I–VIII (Hexagonal Architecture, Saga Orchestration, Delivery Guarantee Floor,
    Shared Event Contracts, Saga Traceability, Security & LGPD, Stable API Contract,
    Observability & Performance)
  - Quality Gates de Engenharia (Section 2)
  - Escopo do Monorepo e Estratégia de Mocks (Section 3)
  - Governance (amendment procedure, versioning policy, exception mechanism, compliance review)
Removed sections: none (template placeholders only)
Deferred TODOs: none — all placeholders resolved from user-provided decisions during interactive
  constitution setup (2026-09-03).
-->

# Conference Back Constitution
<!-- Repositório: conference-back. Domínio atual: serviço de Checkout de e-commerce,
     dentro de um monorepo com 5 microsserviços por bounded context (cart, checkout,
     payment, order, inventory). -->

## Core Principles

### I. Arquitetura Hexagonal (Ports & Adapters) por Serviço (NON-NEGOTIABLE)
O domínio de cada serviço NUNCA importa FastAPI, SQLAlchemy, cliente Kafka ou qualquer
framework/biblioteca de infraestrutura diretamente. Toda dependência externa entra através
de uma porta (interface) e é implementada por um adapter. Isso vale igualmente para os
serviços ainda não construídos (payment, order, inventory, cart): seus fake adapters
in-process DEVEM implementar a mesma porta que o adapter real usará, de modo que a troca de
um pelo outro não exija tocar no domínio do checkout.
Esta é a única fronteira arquitetural do projeto e não aceita exceção documentada — uma
violação só pode ser resolvida corrigindo o código ou emendando esta constituição.

### II. Checkout como Orquestrador de Saga
O checkout é o dono do fluxo de compra, não um participante passivo de coreografia. Ele
mantém uma máquina de estados persistida (ex.: `INICIADO → ESTOQUE_RESERVADO → PAGO →
CONFIRMADO`, incluindo os caminhos de compensação) e envia comandos explícitos a
payment/order/inventory via Kafka, decidindo o próximo passo a partir das respostas
recebidas. Nenhuma lógica de "o que fazer a seguir caso X falhe" pode viver espalhada nos
serviços downstream — ela é centralizada no checkout, de modo que o fluxo de negócio
completo, incluindo os caminhos de erro, seja legível e testável em um único lugar.

### III. Piso de Garantia de Entrega: Outbox + Idempotência + DLQ (NON-NEGOTIABLE)
Todo fluxo do checkout que publica ou consome evento Kafka segue at-least-once com as três
práticas abaixo, sem exceção:
- **Transactional outbox**: o evento é gravado na mesma transação de banco que a mudança de
  estado que o originou; nunca é publicado como efeito colateral fora dessa transação.
- **Consumidor idempotente**: todo consumidor trata reentrega do mesmo evento sem efeito
  colateral duplicado, usando uma chave de idempotência.
- **Dead Letter Queue obrigatória**: mensagens que falham após N tentativas vão para uma DLQ
  monitorada em vez de bloquear o consumo subsequente.
Este piso existe porque o checkout lida com dinheiro e reserva de estoque: uma falha entre
"cobrar o cliente" e "publicar o evento correspondente" sem essas proteções gera cobrança
sem contrapartida. Por isso este princípio é absoluto e não aceita o mecanismo de exceção
justificada descrito em Governança — só muda por emenda formal desta constituição.

### IV. Contratos de Evento via Pacote Interno Compartilhado
Os eventos Kafka trocados entre os serviços do monorepo são modelados como um pacote
interno compartilhado (ex.: `libs/contracts`) usando modelos Pydantic, versionado
semanticamente. Nenhum serviço define seu próprio modelo duplicado para um evento que já
existe no pacote. Toda mudança de campo obrigatório DEVE quebrar um teste de contrato antes
do merge — a incompatibilidade é pega no CI, nunca em produção. Todo produtor e todo
consumidor de evento Kafka tem um teste de contrato validando seu payload contra o pacote.

### V. Rastreabilidade de Saga: Correlation ID + Tracing Distribuído
Toda chamada síncrona e todo evento assíncrono carrega um `saga_id`/`correlation_id`,
propagado desde a chamada de entrada do carrinho até cada consumidor downstream. Tracing
distribuído (OpenTelemetry) é obrigatório, permitindo visualizar o fluxo completo de um
checkout — síncrono e assíncrono — em uma única trace. Logging estruturado em JSON inclui
sempre o `saga_id`, para correlação manual quando o tracing não for suficiente.

### VI. Segurança e Proteção de Dados (LGPD)
Dados sensíveis (número de cartão, CPF e demais dados pessoais/financeiros) NUNCA aparecem
em log, nem crus nem mascarados incorretamente; onde a exposição parcial for inevitável,
mascaramento é obrigatório. O checkout não armazena nem transporta dado de cartão cru — a
tokenização é responsabilidade exclusiva do serviço de payment, e o checkout manipula
apenas tokens/referências opacas.

### VII. Contrato de API Estável
OpenAPI é a fonte da verdade da API síncrona do checkout (a chamada recebida do módulo de
carrinho). A API é versionada explicitamente (ex.: `/v1`); uma mudança breaking exige uma
nova versão de rota, nunca alteração in-place de um contrato já publicado.

### VIII. Observabilidade e Performance como Requisito de Entrega
Toda feature instrumenta métricas de latência e expõe health checks antes de ser
considerada pronta — a ausência de instrumentação bloqueia o merge, independentemente do
resto da funcionalidade estar correta. Não há SLO numérico fixo neste estágio do projeto;
ele será definido a partir de dados reais de produção e documentado quando estabelecido. O
lag de consumo Kafka é a métrica de saúde de referência para o lado assíncrono da saga,
complementando a latência da API síncrona.

## Quality Gates de Engenharia

Todo Pull Request no checkout deve satisfazer, sem exceção, antes de ser elegível a merge:
- **Cobertura de testes**: mínimo de 80%, cobrindo testes unitários e de contrato; PR que
  reduz a cobertura abaixo do limiar é bloqueado automaticamente.
- **Tipagem estática estrita**: `mypy --strict` sem erros; nenhum `Any` implícito; todo
  modelo Pydantic e função pública é tipado.
- **Lint e formatação automática**: `ruff` bloqueia o PR em violação de estilo, import não
  utilizado ou padrão proibido.
- **Teste de contrato por evento**: todo produtor e consumidor Kafka tem teste de contrato
  validando o payload contra o pacote compartilhado (Princípio IV).

## Escopo do Monorepo e Estratégia de Mocks

Este repositório é um monorepo contendo os 5 microsserviços do domínio de e-commerce
delimitados por bounded context: `cart`, `checkout`, `payment`, `order`, `inventory`. O
foco de implementação atual é exclusivamente o **checkout**; os demais quatro serviços
ainda não existem como implementação real.

Enquanto payment, order, inventory e cart não forem implementados, o checkout se integra a
eles através de **fake adapters in-process**: implementações da mesma porta que o adapter
real usará (Princípio I), respondendo em memória com comportamento determinístico e
configurável para os testes. Nenhuma feature de checkout fica bloqueada pela ausência dos
outros serviços — o fake adapter existe justamente para permitir avançar sem eles. Quando
um serviço real for construído, sua adoção é uma troca de adapter, não uma mudança no
domínio do checkout.

## Build e Deployment

Cada microsserviço do monorepo (`cart`, `checkout`, `payment`, `order`, `inventory`) tem seu
próprio `Dockerfile`, localizado dentro da pasta do próprio serviço (ex.:
`services/checkout/Dockerfile`, `services/payment/Dockerfile`). Cada serviço é autocontido
quanto à sua imagem de container — nenhum `Dockerfile` é compartilhado entre serviços.

Cada microsserviço tem sua própria branch de release dedicada (ex.: `release/checkout`,
`release/payment`), independente das demais. Os manifestos Kubernetes de deploy daquele
serviço vivem nessa branch de release, versionados e promovidos separadamente do
código-fonte em desenvolvimento/main. Isso permite que cada serviço seja implantado de forma
independente, sem acoplar o ciclo de release de um serviço ao dos outros quatro.

A branch de release de um serviço só recebe atualização de manifesto quando aquele serviço
tem uma nova versão pronta para deploy — não é sincronizada automaticamente a cada commit em
main.

## Governance

Esta constituição tem precedência sobre qualquer prática, convenção de time ou decisão de
plano individual em caso de conflito.

**Princípios NON-NEGOTIABLE** (Arquitetura Hexagonal — Princípio I; Piso de Garantia de
Entrega — Princípio III): não admitem o mecanismo de exceção abaixo. Uma necessidade real de
desviar deles só pode ser resolvida por emenda formal desta constituição, nunca por
justificativa pontual em um `plan.md`.

**Exceções para os demais princípios**: quando uma feature precisar violar um princípio não
listado como NON-NEGOTIABLE, a exceção deve ser documentada explicitamente no `plan.md` da
feature, incluindo a justificativa e as alternativas descartadas. A exceção vale apenas para
aquela feature; não estabelece precedente automático para as demais.

**Processo de emenda**: qualquer mudança nesta constituição — adição, remoção ou
redefinição de princípio — é proposta via alteração deste arquivo, revisada quanto a
impacto nos templates dependentes (`plan-template.md`, `spec-template.md`,
`tasks-template.md`) e registrada no Sync Impact Report no topo do arquivo.

**Política de versionamento semântico**:
- **MAJOR**: remoção ou redefinição incompatível de um princípio existente.
- **MINOR**: adição de novo princípio ou expansão material de uma seção existente.
- **PATCH**: esclarecimentos de redação, correções e refinamentos não semânticos.

**Revisão de conformidade**: todo Pull Request deve ser avaliado quanto à aderência aos
princípios desta constituição antes do merge, adicionalmente aos Quality Gates de
Engenharia.

**Version**: 1.1.0 | **Ratified**: 2026-09-03 | **Last Amended**: 2026-09-03
