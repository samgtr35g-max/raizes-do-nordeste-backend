# Decisões de Escopo e Premissas

Este documento registra as decisões de escopo e premissas oficiais do projeto
**Rede Raízes do Nordeste — Back-End**, tomadas durante a modelagem conceitual.

## 1. Usuario e Cliente permanecem como entidades separadas

- `Cliente.usuarioId` é opcional.
- `Usuario` representa autenticação, papéis e permissões.
- `Cliente` representa o consumidor e seus dados pessoais/LGPD.

## 2. Promoções serão simplificadas para o MVP

- Remover `PromocaoProduto`.
- Remover `PromocaoUnidade`.
- `Promocao` terá `produtoId` opcional.
- `produtoId` preenchido = promoção específica de produto.
- `produtoId` nulo = promoção geral da rede.
- Manter `nome`, `descricao`, `tipoDesconto`, `valor`, `dataInicio`, `dataFim` e `ativa`.

## 3. UsuarioPapel não terá unidadeId

- `UsuarioPapel` será composto apenas por `usuarioId` e `papelId`.
- `Usuario.unidadeId` define a unidade do usuário.
- `unidadeId` nulo representa administrador com acesso à rede/todas as unidades.
- Premissa: um usuário pertence a uma única unidade no MVP.
