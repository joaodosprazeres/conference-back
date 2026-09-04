# Feature Specification: Iniciar Checkout

**Feature Branch**: `001-iniciar-checkout`

**Created**: 2026-09-03

**Status**: Draft

**Input**: User description: "Como cliente convidado (sem necessidade de login), ao decidir finalizar minha compra a partir do carrinho, preciso que o sistema de checkout inicie uma sessão de checkout com base no meu carrinho atual, para que eu possa prosseguir com a compra. O módulo de carrinho envia o id do carrinho e a lista de itens com quantidade e preço unitário no momento da chamada. O checkout cria uma sessão de checkout com estado inicial, calcula o valor total da compra e define um prazo de expiração para essa sessão, retornando o id da sessão, o total calculado e o prazo de expiração ao chamador. Esta feature não coleta dados do convidado (e-mail, endereço), não recebe método de pagamento, não aplica cupons ou descontos, e não aciona ainda os serviços de pagamento, pedido ou estoque — isso fica para uma feature de confirmação do checkout, posterior. Uma vez iniciado o checkout, o carrinho de origem fica congelado (não pode mais ser editado enquanto essa sessão de checkout existir)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Iniciar checkout a partir do carrinho (Priority: P1)

Como cliente convidado, ao decidir finalizar minha compra, quero que o sistema crie uma
sessão de checkout a partir do meu carrinho atual, para que eu saiba o valor total a pagar e
o prazo que tenho para concluir a compra antes de prosseguir para as próximas etapas.

**Why this priority**: É o ponto de entrada de todo o fluxo de compra. Sem esta capacidade,
nenhuma etapa seguinte (confirmação, pagamento, criação do pedido) pode existir. É o menor
fatiamento que já entrega valor observável: o cliente sai do carrinho e entra formalmente em
um processo de compra com total e prazo definidos.

**Independent Test**: Pode ser testada isoladamente enviando um carrinho válido (id + itens
com quantidade e preço) para o início do checkout e verificando que uma sessão é criada com
total calculado corretamente e prazo de expiração definido — sem depender de nenhuma outra
funcionalidade ainda não construída (pagamento, pedido, estoque).

**Acceptance Scenarios**:

1. **Given** um cliente convidado com um carrinho contendo um ou mais itens, **When** ele
   decide prosseguir para o checkout, **Then** o sistema cria uma sessão de checkout em
   estado inicial e retorna o id da sessão, o total calculado e o prazo de expiração.
2. **Given** um carrinho com múltiplos itens de quantidades e preços unitários diferentes,
   **When** o checkout é iniciado, **Then** o total calculado corresponde à soma de
   quantidade × preço unitário de todos os itens recebidos.
3. **Given** uma sessão de checkout ativa para um carrinho, **When** alguém tenta editar
   esse carrinho de origem, **Then** a edição não é permitida enquanto a sessão existir.
4. **Given** uma sessão de checkout que atingiu seu prazo de expiração sem confirmação,
   **When** o prazo é ultrapassado, **Then** a sessão passa a ser considerada expirada e o
   carrinho de origem volta a poder ser editado.

---

### Edge Cases

- O que acontece quando o prazo de expiração de uma sessão é atingido sem que o checkout
  tenha sido confirmado? A sessão passa para um estado de expirada e o carrinho de origem é
  liberado para edição novamente (ver Acceptance Scenario 4).
- O que acontece se o módulo de carrinho enviar uma nova solicitação de início de checkout
  para um carrinho que já possui uma sessão de checkout ativa? Nesta versão, uma nova sessão
  independente é criada; não há verificação de sessão duplicada (ver Assumptions).
- O que acontece se os itens recebidos do carrinho estiverem malformados (lista vazia,
  quantidade ou preço inválidos)? Esta feature assume que o módulo de carrinho só envia
  dados estruturalmente válidos e não realiza validação de negócio adicional sobre isso (ver
  Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir que um cliente convidado inicie uma sessão de checkout
  informando o id do carrinho e a lista de itens (produto, quantidade, preço unitário) no
  momento da chamada.
- **FR-002**: O sistema DEVE criar uma sessão de checkout em um estado inicial a cada
  solicitação de início recebida.
- **FR-003**: O sistema DEVE calcular o valor total da sessão como a soma de quantidade ×
  preço unitário de todos os itens recebidos na solicitação.
- **FR-004**: O sistema DEVE atribuir um prazo de expiração a toda sessão de checkout criada.
- **FR-005**: O sistema DEVE retornar ao chamador o id da sessão de checkout, o total
  calculado e o prazo de expiração, imediatamente após a criação da sessão.
- **FR-006**: O sistema NÃO DEVE exigir dados de identificação do convidado (e-mail,
  endereço de entrega) para iniciar uma sessão de checkout.
- **FR-007**: O sistema NÃO DEVE aceitar nem armazenar um método de pagamento durante o
  início do checkout.
- **FR-008**: O sistema NÃO DEVE aplicar cupons ou descontos ao total calculado nesta etapa;
  o total reflete exclusivamente os itens e preços recebidos.
- **FR-009**: O sistema NÃO DEVE acionar os serviços de pagamento, pedido ou estoque durante
  o início do checkout.
- **FR-010**: O carrinho de origem DEVE ser impedido de sofrer edições enquanto sua sessão de
  checkout associada estiver ativa (não expirada).
- **FR-011**: Ao atingir o prazo de expiração sem confirmação, a sessão de checkout DEVE
  passar a um estado de expirada e o carrinho de origem DEVE voltar a ser editável.
- **FR-012**: O sistema DEVE usar os dados de itens (quantidade, preço unitário) exatamente
  como recebidos na solicitação de início, sem consultar novamente o módulo de carrinho para
  obter valores atualizados.

### Key Entities

- **Sessão de Checkout**: representa um processo de compra em andamento, iniciado a partir
  de um carrinho. Atributos principais: id da sessão, id do carrinho de origem, snapshot dos
  itens (produto, quantidade, preço unitário), total calculado, estado (ex.: iniciada,
  expirada), prazo de expiração, data/hora de criação.
- **Item do Carrinho (snapshot)**: dado de um item capturado no momento do início do
  checkout — produto, quantidade e preço unitário — desacoplado do estado atual do módulo de
  carrinho, que pode mudar depois.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Clientes convidados recebem a confirmação de início do checkout — com total e
  prazo — em até 2 segundos após decidirem prosseguir com a compra.
- **SC-002**: 100% das solicitações de início de checkout com carrinho válido produzem uma
  sessão cujo total corresponde exatamente à soma de quantidade × preço unitário dos itens
  informados.
- **SC-003**: 100% dos carrinhos com sessão de checkout ativa permanecem não editáveis
  durante toda a vigência dessa sessão.
- **SC-004**: 100% das sessões de checkout criadas possuem um prazo de expiração definido e
  consultável.

## Assumptions

- O módulo de carrinho é responsável por garantir que o carrinho enviado é estruturalmente
  válido (lista não vazia, quantidades e preços positivos) antes de chamar o início do
  checkout; esta feature não revalida essas condições.
- Múltiplas sessões de checkout podem ser criadas para o mesmo carrinho nesta versão; a
  prevenção de sessões duplicadas/concorrentes fica para uma iteração futura.
- A duração exata do prazo de expiração foi fixada em 15 minutos durante o planejamento
  técnico (ver plan.md e data-model.md), não sendo detalhada nesta especificação.
- O congelamento do carrinho de origem é um comportamento observável de negócio nesta
  especificação; os detalhes de como o módulo de carrinho e o checkout coordenam esse estado
  entre si são decisão de planejamento técnico, não desta especificação.
- Nenhum perfil de cliente é criado ou persistido nesta feature; a identidade do convidado
  neste estágio se resume ao carrinho de origem.
- Método de pagamento, dados de entrega/contato do convidado, cupons/descontos e o
  acionamento de payment/order/inventory pertencem a uma feature futura de confirmação do
  checkout, fora do escopo desta especificação.
