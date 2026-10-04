# LGPD, Privacidade e Auditoria

Documento academico do projeto **Rede Raizes do Nordeste - Back-End**.
Descreve, de forma simples, como o sistema trata dados pessoais, aplica
medidas de protecao (LGPD) e registra auditoria das acoes sensiveis.

> Este documento nao define prazos legais nem politica juridica especifica.
> Ele reflete apenas o que foi implementado no codigo.

## 1. Dados pessoais tratados

| Dado | Onde | Observacao |
|---|---|---|
| nome | `Cliente.nome` | identificacao |
| CPF | `Cliente.cpf` | opcional (pode ser `NULL`) |
| email | `Cliente.email` / `Usuario.email` | contato/login |
| telefone | `Cliente.telefone` | contato |
| data de nascimento | `Cliente.dataNascimento` | opcional |
| consentimento | `Cliente.aceitaComunicacoes` / `Cliente.consentimentoEm` | comunicacao |
| dados de pedidos | `Pedido`, `ItemPedido` | operacao, sem dados sensiveis de pagamento |

Nao sao tratados nem armazenados: numero de cartao, CVV, senha em texto puro,
tokens ou segredos.

## 2. Finalidade

- identificacao do cliente;
- realizacao e acompanhamento de pedidos;
- programa de fidelidade (acumulo/resgate de pontos);
- comunicacao, **somente quando autorizada** (`aceitaComunicacoes`);
- auditoria e seguranca.

## 3. Protecao

- **Senhas**: armazenadas apenas como hash (Werkzeug), nunca em texto puro e
  nunca retornadas pela API.
- **JWT**: segredo vem de variavel de ambiente; o token nao e gravado no banco
  nem em logs.
- **Controle de acesso**: RBAC (papeis/permissao) e escopo por unidade; cliente
  autenticado acessa apenas os proprios dados.
- **Minimizacao**: a auditoria registra apenas o necessario (quem, o que, em
  qual entidade, quando, resultado) e **mascara** campos sensiveis.
- **Nao armazenamento de dados reais de cartao**: o pagamento usa um gateway
  simulado (mock) que nunca recebe cartao/CVV.
- **Auditoria**: toda acao sensivel relevante gera um registro em
  `LogAuditoria`, dentro da mesma transacao da operacao.

## 4. Consentimento

- `Cliente.aceitaComunicacoes` indica se o cliente aceita receber comunicacoes.
- `Cliente.consentimentoEm` registra quando o consentimento foi dado.
- A anonimizacao (`POST /clientes/{id}/anonimizacao`) zera
  `aceitaComunicacoes`, respeitando a revogacao.

## 5. Retencao e anonimizacao

- Dados podem precisar ser mantidos para obrigacoes operacionais e de
  auditoria; por isso **nao apagamos registros historicos automaticamente**
  (isso quebraria integridade referencial de pedidos/fidelidade).
- A **anonimizacao** remove os dados pessoais do cliente, preservando o
  registro e as FKs:
  - `nome` -> `ANONIMIZADO`
  - `cpf`, `email`, `telefone`, `dataNascimento` -> `NULL`
  - `anonimizado` -> `true`
- A anonimizacao e auditada (acao `ANONIMIZACAO`).

## 6. Auditoria

Servico: `app/infrastructure/audit/auditoria.py` (`registrar_auditoria`).
Persiste em `LogAuditoria` (tabela ja existente) **sem commit proprio**, para
respeitar a transacao da operacao: se a operacao sofrer rollback, a auditoria
tambem e desfeita.

Campos sensiveis (senha, senhaHash, token, authorization, jwt, cvv, cartao,
numero_cartao, entre outros) sao **mascarados** (`***`) antes de salvar.

### Acoes auditadas

| Acao | Fluxo |
|---|---|
| `LOGIN` | login bem-sucedido |
| `LOGIN_NEGADO` | credenciais invalidas ou usuario inativo (sem registrar senha) |
| `ESTOQUE_ENTRADA` / `ESTOQUE_SAIDA` / `ESTOQUE_AJUSTE` | movimentacoes de estoque |
| `CRIACAO` | criacao de pedido |
| `ALTERACAO_STATUS` | mudanca de status do pedido |
| `CANCELAMENTO` | cancelamento de pedido |
| `PAGAMENTO_APROVADO` / `PAGAMENTO_RECUSADO` | resultado do pagamento |
| `RESGATE_PONTOS` / `ESTORNO_PONTOS` | fidelidade |
| `ANONIMIZACAO` | remocao de dados pessoais do cliente |

## 7. Controle de acesso aos dados do cliente

- O cliente vinculado a um `Usuario` (`Cliente.usuarioId`) acessa **apenas os
  proprios** dados de fidelidade/anonimizacao.
- Usuarios internos (com papel) acessam conforme a regra do sistema.
- Tentativa de acessar outro cliente por troca de ID na URL retorna **403**.
- Nao existe papel `CLIENTE`; o acesso do cliente e por titularidade.
