# Especificação Lógica do DER

Especificação conceitual/lógica das entidades do projeto **Rede Raízes do Nordeste — Back-End**,
para posterior desenho do DER.

Fontes: `decisoes-de-escopo-e-premissas.md`, `regras-de-negocio.md`, modelo conceitual revisado
e requisitos obrigatórios do projeto.

> Modelo com **19 entidades**. Nenhuma entidade é criada, removida ou renomeada neste documento.

## 1. Usuario

- **Finalidade:** autenticação, papéis e permissões (equipe interna; e, opcionalmente, cliente com login).
- **Atributos:** id, nome, email, senhaHash, ativo, unidadeId, criadoEm, atualizadoEm.
- **PK:** id.
- **FKs:** unidadeId → Unidade(id) (nulo permitido).
- **Relacionamentos:** N:1 Unidade; N:N Papel (via UsuarioPapel); 1:1 opcional com Cliente (do lado de Cliente).
- **Cardinalidades:** Unidade 1:N Usuario · Usuario N:N Papel · Usuario 1:1 Cliente (opcional).
- **Restrições:** email único; senhaHash obrigatório; unidadeId nulo = administrador da rede.

## 2. Papel

- **Finalidade:** agrupar permissões (ex: ADMIN, GERENTE, ATENDENTE, COZINHA).
- **Atributos:** id, nome, descricao.
- **PK:** id. **FKs:** nenhuma.
- **Relacionamentos:** N:N Usuario (via UsuarioPapel); N:N Permissao (via PapelPermissao).
- **Cardinalidades:** Papel N:N Usuario · Papel N:N Permissao.
- **Restrições:** nome único.

## 3. Permissao

- **Finalidade:** representar uma ação autorizável (ex: `ESTOQUE_AJUSTAR`).
- **Atributos:** id, codigo, descricao.
- **PK:** id. **FKs:** nenhuma.
- **Relacionamentos:** N:N Papel (via PapelPermissao).
- **Cardinalidades:** Permissao N:N Papel.
- **Restrições:** codigo único.

## 4. UsuarioPapel

- **Finalidade:** ligar Usuario a Papel.
- **Atributos:** usuarioId, papelId, atribuidoEm.
- **PK:** composta (usuarioId, papelId).
- **FKs:** usuarioId → Usuario(id); papelId → Papel(id).
- **Relacionamentos:** N:1 Usuario; N:1 Papel.
- **Cardinalidades:** resolve o N:N Usuario–Papel.
- **Restrições:** PK composta evita duplicidade; sem unidadeId (premissa 3).

## 5. PapelPermissao

- **Finalidade:** ligar Papel a Permissao.
- **Atributos:** papelId, permissaoId.
- **PK:** composta (papelId, permissaoId).
- **FKs:** papelId → Papel(id); permissaoId → Permissao(id).
- **Relacionamentos:** N:1 Papel; N:1 Permissao.
- **Cardinalidades:** resolve o N:N Papel–Permissao.

## 6. Cliente

- **Finalidade:** consumidor e seus dados pessoais (LGPD).
- **Atributos:** id, nome, cpf, email, telefone, dataNascimento, usuarioId, aceitaComunicacoes, consentimentoEm, anonimizado, criadoEm.
- **PK:** id.
- **FKs:** usuarioId → Usuario(id) (nulo permitido; único quando preenchido).
- **Relacionamentos:** 1:1 opcional Usuario; 1:1 ContaFidelidade; 1:N Pedido.
- **Cardinalidades:** Cliente 1:1 Usuario (opcional) · Cliente 1:1 ContaFidelidade · Cliente 1:N Pedido.
- **Restrições:** usuarioId único quando não nulo; cpf único somente quando preenchido; cpf vazio = NULL.

## 7. Unidade

- **Finalidade:** cada filial da rede.
- **Atributos:** id, nome, cnpj, endereco, cidade, uf, telefone, ativo.
- **PK:** id. **FKs:** nenhuma.
- **Relacionamentos:** 1:N Usuario; 1:N Estoque; 1:N Pedido.
- **Cardinalidades:** Unidade 1:N Usuario · 1:N Estoque · 1:N Pedido.
- **Restrições:** cnpj único.

## 8. Categoria

- **Finalidade:** organizar o cardápio.
- **Atributos:** id, nome, ativo.
- **PK:** id. **FKs:** nenhuma.
- **Relacionamentos:** 1:N Produto.
- **Cardinalidades:** Categoria 1:N Produto.
- **Restrições:** nome único.

## 9. Produto

- **Finalidade:** item do cardápio vendido na rede.
- **Atributos:** id, nome, descricao, precoBase, categoriaId, ativo.
- **PK:** id.
- **FKs:** categoriaId → Categoria(id).
- **Relacionamentos:** N:1 Categoria; 1:N ItemPedido; 1:N Estoque; 1:N Promocao.
- **Cardinalidades:** Categoria 1:N Produto · Produto 1:N ItemPedido · 1:N Estoque · 1:N Promocao.
- **Restrições:** precoBase ≥ 0.

## 10. Estoque

- **Finalidade:** quantidade de um produto em uma unidade específica.
- **Atributos:** id, unidadeId, produtoId, quantidadeAtual, quantidadeMinima, atualizadoEm.
- **PK:** id.
- **FKs:** unidadeId → Unidade(id); produtoId → Produto(id).
- **Relacionamentos:** N:1 Unidade; N:1 Produto; 1:N MovimentacaoEstoque.
- **Cardinalidades:** Unidade 1:N Estoque · Produto 1:N Estoque · Estoque 1:N MovimentacaoEstoque.
- **Restrições:** chave candidata composta UNIQUE(unidadeId, produtoId); quantidadeAtual ≥ 0.

## 11. MovimentacaoEstoque

- **Finalidade:** histórico de entradas/saídas/ajustes de estoque.
- **Atributos:** id, estoqueId, tipo, quantidade, motivo, pedidoId, usuarioId, criadoEm.
- **PK:** id.
- **FKs:** estoqueId → Estoque(id); pedidoId → Pedido(id) (**opcional**); usuarioId → Usuario(id) (nulo permitido).
- **Relacionamentos:** N:1 Estoque; N:1 Pedido (opcional); N:1 Usuario (opcional).
- **Cardinalidades:** Estoque 1:N MovimentacaoEstoque.
- **Restrições:** tipo ∈ {ENTRADA, SAIDA, AJUSTE}; quantidade > 0.
- **Observação:** `pedidoId` é **opcional**. Um pedido pode gerar movimentações de estoque,
  mas uma movimentação também pode existir **sem estar vinculada a um pedido** — por exemplo,
  em uma entrada de mercadoria ou um ajuste manual de inventário.

## 12. Pedido

- **Finalidade:** registrar uma compra.
- **Atributos:** id, unidadeId, clienteId, usuarioId, canalPedido, status, valorProdutos, valorDesconto, valorTotal, observacao, criadoEm, atualizadoEm.
- **PK:** id.
- **FKs:** unidadeId → Unidade(id); clienteId → Cliente(id) (nulo permitido); usuarioId → Usuario(id) (nulo permitido).
- **Relacionamentos:** N:1 Unidade; N:1 Cliente (opcional); N:1 Usuario (opcional); 1:N ItemPedido; 1:N Pagamento; 1:N HistoricoStatusPedido; 1:N MovimentacaoEstoque (referência opcional); 1:N MovimentacaoPontos (referência opcional).
- **Cardinalidades:** Unidade 1:N Pedido · Cliente 1:N Pedido · Pedido 1:N ItemPedido · 1:N Pagamento · 1:N HistoricoStatusPedido.
- **Restrições:** canalPedido obrigatório ∈ {APP, TOTEM, BALCAO, PICKUP, WEB}; status conforme transições; deve ter ≥ 1 ItemPedido; valorTotal = valorProdutos − valorDesconto (snapshot).

## 13. ItemPedido

- **Finalidade:** cada linha do pedido.
- **Atributos:** id, pedidoId, produtoId, quantidade, valorUnitario, valorTotalItem, observacao.
- **PK:** id.
- **FKs:** pedidoId → Pedido(id); produtoId → Produto(id).
- **Relacionamentos:** N:1 Pedido; N:1 Produto.
- **Cardinalidades:** Pedido 1:N ItemPedido · Produto 1:N ItemPedido.
- **Restrições:** quantidade > 0; valorUnitario = preço praticado no momento da venda (snapshot); valorTotalItem = quantidade × valorUnitario.

## 14. HistoricoStatusPedido

- **Finalidade:** trilha do fluxo de status do pedido.
- **Atributos:** id, pedidoId, statusAnterior, statusNovo, usuarioId, observacao, criadoEm.
- **PK:** id.
- **FKs:** pedidoId → Pedido(id); usuarioId → Usuario(id) (nulo permitido).
- **Relacionamentos:** N:1 Pedido; N:1 Usuario (opcional).
- **Cardinalidades:** Pedido 1:N HistoricoStatusPedido.
- **Restrições:** apenas transições válidas.

## 15. Pagamento

- **Finalidade:** registrar o pagamento, desacoplado do pedido (permite pagamento externo simulado).
- **Atributos:** id, pedidoId, valor, metodo, status, provedor, idTransacaoExterna, payloadResposta, criadoEm, atualizadoEm.
- **PK:** id.
- **FKs:** pedidoId → Pedido(id).
- **Relacionamentos:** N:1 Pedido.
- **Cardinalidades:** Pedido 1:N Pagamento.
- **Restrições:** status ∈ {PENDENTE, APROVADO, RECUSADO, ESTORNADO}; idTransacaoExterna único quando não nulo; não embutido no Pedido.

## 16. ContaFidelidade

- **Finalidade:** saldo de pontos do cliente.
- **Atributos:** id, clienteId, saldoPontos, atualizadoEm.
- **PK:** id.
- **FKs:** clienteId → Cliente(id) (único).
- **Relacionamentos:** 1:1 Cliente; 1:N MovimentacaoPontos.
- **Cardinalidades:** Cliente 1:1 ContaFidelidade · ContaFidelidade 1:N MovimentacaoPontos.
- **Restrições:** clienteId único (garante 1:1); saldoPontos ≥ 0.

## 17. MovimentacaoPontos

- **Finalidade:** histórico de acúmulo/resgate/estorno de pontos.
- **Atributos:** id, contaFidelidadeId, tipo, pontos, pedidoId, criadoEm.
- **PK:** id.
- **FKs:** contaFidelidadeId → ContaFidelidade(id); pedidoId → Pedido(id) (nulo permitido).
- **Relacionamentos:** N:1 ContaFidelidade; N:1 Pedido (opcional).
- **Cardinalidades:** ContaFidelidade 1:N MovimentacaoPontos.
- **Restrições:** tipo ∈ {ACUMULO, RESGATE, ESTORNO, EXPIRACAO}; saldo sempre coerente com as movimentações.
- **Observação:** `ESTORNO` representa a reversão de pontos anteriormente concedidos ou resgatados,
  especialmente em cancelamentos, mantendo o saldo da conta coerente.

## 18. Promocao

- **Finalidade:** promoções/campanhas (simplificada).
- **Atributos:** id, nome, descricao, tipoDesconto, valor, dataInicio, dataFim, ativa, produtoId.
- **PK:** id.
- **FKs:** produtoId → Produto(id) (nulo permitido).
- **Relacionamentos:** N:1 Produto (opcional).
- **Cardinalidades:** Produto 1:N Promocao.
- **Restrições:** dataFim ≥ dataInicio; tipoDesconto ∈ {PERCENTUAL, VALOR_FIXO}; produtoId nulo = promoção geral da rede.
- **Observação:** produtoId preenchido = promoção específica; produtoId nulo = promoção geral.
  Se existir promoção geral e específica aplicáveis ao mesmo produto, somente a de maior
  benefício é aplicada. Nunca há desconto duplicado.

## 19. LogAuditoria

- **Finalidade:** rastreabilidade de ações (quem fez o quê, quando).
- **Atributos:** id, usuarioId, entidade, entidadeId, acao, dadosAnteriores, dadosNovos, ip, criadoEm.
- **PK:** id.
- **FKs:** usuarioId → Usuario(id) (nulo permitido).
- **Relacionamentos:** N:1 Usuario (opcional).
- **Cardinalidades:** Usuario 1:N LogAuditoria.
- **Restrições:** somente inserção; sem senha/token; dados pessoais mascarados/minimizados.

---

# Destaques

## Relacionamentos 1:1

- Cliente ↔ Usuario — via `Cliente.usuarioId` (opcional, único quando preenchido).
- Cliente ↔ ContaFidelidade — via `ContaFidelidade.clienteId` (único).

## Relacionamentos 1:N

- Unidade → Usuario · Unidade → Estoque · Unidade → Pedido
- Categoria → Produto
- Produto → Estoque · Produto → ItemPedido · Produto → Promocao
- Estoque → MovimentacaoEstoque
- Cliente → Pedido
- Pedido → ItemPedido · Pedido → Pagamento · Pedido → HistoricoStatusPedido · Pedido → MovimentacaoEstoque (opc.) · Pedido → MovimentacaoPontos (opc.)
- ContaFidelidade → MovimentacaoPontos
- Usuario → MovimentacaoEstoque (opc.) · Usuario → HistoricoStatusPedido (opc.) · Usuario → LogAuditoria (opc.)

## Relacionamentos N:N (representados por tabelas de junção)

- Usuario ↔ Papel via UsuarioPapel — PK composta (usuarioId, papelId).
- Papel ↔ Permissao via PapelPermissao — PK composta (papelId, permissaoId).

## Chaves compostas

- UsuarioPapel: PK (usuarioId, papelId).
- PapelPermissao: PK (papelId, permissaoId).
- Estoque: PK id, com chave candidata UNIQUE (unidadeId, produtoId).

## Restrições de integridade importantes

- Estoque: UNIQUE(unidadeId, produtoId) e quantidadeAtual ≥ 0.
- Pedido: canalPedido obrigatório e enumerado; ≥ 1 item; valores recalculados no servidor.
- ItemPedido: quantidade > 0; valorUnitario como snapshot.
- Pagamento: desacoplado; idTransacaoExterna único quando presente.
- Cliente: cpf/usuarioId únicos somente quando preenchidos; CPF vazio = NULL.
- LogAuditoria: apenas inserção; sem segredos; dados pessoais mascarados.
- Promocao: período coerente; uma única promoção por item/pedido.
- MovimentacaoEstoque.pedidoId opcional (entrada/ajuste manual sem pedido).

---

# Verificação de consistência

- Toda FK aponta para uma PK existente.
- Nenhum relacionamento sem origem/destino.
- Estoque específico por unidade + produto (UNIQUE unidadeId + produtoId).
- Pedido possui itens (≥ 1 ItemPedido).
- Item guarda o preço praticado na venda (`ItemPedido.valorUnitario`).
- Pagamento desacoplado do pedido (entidade própria, N:1 Pedido).
- Cliente.usuarioId opcional.
- Promocao.produtoId opcional.
- UsuarioPapel sem unidadeId.
- canalPedido obrigatório no Pedido.

## Mapa de FKs → PKs

- Usuario.unidadeId → Unidade.id
- Cliente.usuarioId → Usuario.id
- Produto.categoriaId → Categoria.id
- Estoque.unidadeId → Unidade.id · Estoque.produtoId → Produto.id
- MovimentacaoEstoque.estoqueId → Estoque.id · .pedidoId → Pedido.id · .usuarioId → Usuario.id
- Pedido.unidadeId → Unidade.id · .clienteId → Cliente.id · .usuarioId → Usuario.id
- ItemPedido.pedidoId → Pedido.id · .produtoId → Produto.id
- HistoricoStatusPedido.pedidoId → Pedido.id · .usuarioId → Usuario.id
- Pagamento.pedidoId → Pedido.id
- ContaFidelidade.clienteId → Cliente.id
- MovimentacaoPontos.contaFidelidadeId → ContaFidelidade.id · .pedidoId → Pedido.id
- Promocao.produtoId → Produto.id
- LogAuditoria.usuarioId → Usuario.id
- UsuarioPapel.usuarioId → Usuario.id · .papelId → Papel.id
- PapelPermissao.papelId → Papel.id · .permissaoId → Permissao.id
