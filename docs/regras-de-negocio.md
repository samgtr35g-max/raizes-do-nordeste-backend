# Regras de Negócio

Regras de negócio oficiais do projeto **Rede Raízes do Nordeste — Back-End**.
Complementa as decisões registradas em `decisoes-de-escopo-e-premissas.md`.

## 1. Promoções

- No máximo uma promoção será aplicada a cada item/pedido.
- `Promocao.produtoId` preenchido = promoção específica de um produto.
- `Promocao.produtoId` nulo = promoção geral da rede.
- Se existir promoção geral e promoção específica aplicáveis ao mesmo produto, somente a de maior benefício será aplicada.
- Nunca haverá desconto duplicado pela combinação de promoções.

## 2. Autorização de clientes

- Não criar o papel RBAC "CLIENTE".
- Clientes autenticados serão autorizados por propriedade.
- Um cliente vinculado a um Usuario poderá acessar apenas seus próprios dados e seus próprios pedidos.
- Usuários internos continuam utilizando Papel/Permissao para autorização.
- A API deverá validar a propriedade antes de permitir acesso a recursos do cliente.

## 3. Auditoria e LGPD

- LogAuditoria nunca deve armazenar senha, token ou outros segredos.
- Dados pessoais não devem ser armazenados em texto puro nos campos de dados anteriores/novos.
- Quando necessário registrar alterações, utilizar apenas campos relevantes e valores mascarados, minimizados ou anonimizados.

## 4. Valores do pedido

- `valorProdutos`, `valorDesconto` e `valorTotal` permanecem no pedido como snapshot.
- Esses valores sempre serão calculados/recalculados pelo servidor.
- Nunca confiar em valores monetários enviados pelo cliente.

## 5. Status do pedido

Transições válidas:

- RECEBIDO → EM_PREPARO
- EM_PREPARO → PRONTO
- PRONTO → CONCLUIDO
- RECEBIDO → CANCELADO
- EM_PREPARO → CANCELADO
- PRONTO → CANCELADO

`CONCLUIDO` representa o pedido entregue/finalizado. `CANCELADO` é estado permitido apenas nas transições acima. Não permitir transições inválidas, como CONCLUIDO → EM_PREPARO.

## 6. Cancelamento / Estorno

Quando um pedido cancelado já tiver causado efeitos financeiros ou de estoque:

- gerar movimentação de estoque de ENTRADA para devolver as quantidades;
- gerar movimentação de pontos de estorno quando pontos já tiverem sido concedidos;
- atualizar o pagamento para ESTORNADO quando houver pagamento aprovado passível de estorno;
- registrar a alteração no histórico do pedido e na auditoria quando aplicável.

## 7. CPF

- CPF não informado deve ser armazenado como NULL, e não como string vazia.
- A unicidade deve ser aplicada somente quando o CPF estiver preenchido.

## 8. Contagem

- Considerar o modelo atual com 19 entidades.
- Não adicionar novas entidades neste momento.
