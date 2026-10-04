from decimal import Decimal

from sqlalchemy import select, update

from app.domain.exceptions import (
    EstoqueInsuficienteError,
    RecursoNaoEncontradoError,
    TransicaoStatusInvalidaError,
    ValidacaoError,
)
from app.application.use_cases.fidelidade import estornar_pontos_por_pedido
from app.application.use_cases.promocoes import calcular_desconto
from app.infrastructure.audit.auditoria import registrar_auditoria
from app.infrastructure.database import db
from app.infrastructure.database.models import (
    Cliente,
    Estoque,
    HistoricoStatusPedido,
    ItemPedido,
    MovimentacaoEstoque,
    Pedido,
    Produto,
    Unidade,
)
from app.infrastructure.database.models.pedido import CANAL_PEDIDO, STATUS_PEDIDO

TRANSICOES_PERMITIDAS = {
    "RECEBIDO": {"EM_PREPARO"},
    "EM_PREPARO": {"PRONTO"},
    "PRONTO": {"CONCLUIDO"},
    "CONCLUIDO": set(),
    "CANCELADO": set(),
}

STATUS_CANCELAVEIS = {"RECEBIDO", "EM_PREPARO", "PRONTO"}


def listar_pedidos(unidade_id=None, canal_pedido=None, status=None):
    stmt = select(Pedido)
    if unidade_id is not None:
        stmt = stmt.where(Pedido.unidadeId == unidade_id)
    if canal_pedido is not None:
        stmt = stmt.where(Pedido.canalPedido == canal_pedido)
    if status is not None:
        stmt = stmt.where(Pedido.status == status)
    stmt = stmt.order_by(Pedido.id)
    return db.session.scalars(stmt).all()


def obter_pedido(pedido_id):
    pedido = db.session.get(Pedido, pedido_id)
    if pedido is None:
        raise RecursoNaoEncontradoError("Pedido nao encontrado.")
    return pedido


def _registrar_historico(pedido_id, status_anterior, status_novo, usuario_id, observacao):
    db.session.add(
        HistoricoStatusPedido(
            pedidoId=pedido_id,
            statusAnterior=status_anterior,
            statusNovo=status_novo,
            usuarioId=usuario_id,
            observacao=observacao,
        )
    )


def _validar_item(item):
    if not isinstance(item, dict):
        raise ValidacaoError("Item invalido.")
    produto_id = item.get("produtoId")
    quantidade = item.get("quantidade")
    if isinstance(produto_id, bool) or not isinstance(produto_id, int):
        raise ValidacaoError("produtoId invalido.")
    if isinstance(quantidade, bool) or not isinstance(quantidade, int):
        raise ValidacaoError("A quantidade deve ser um numero inteiro.")
    if quantidade <= 0:
        raise ValidacaoError("A quantidade deve ser maior que zero.")
    return produto_id, quantidade, item.get("observacao")


def criar_pedido(unidade_id, canal_pedido, itens, cliente_id=None, usuario_id=None, observacao=None, ip=None):
    if canal_pedido not in CANAL_PEDIDO:
        raise ValidacaoError("Canal de pedido invalido.")
    if not isinstance(itens, list) or not itens:
        raise ValidacaoError("Informe ao menos um item.")

    unidade = db.session.get(Unidade, unidade_id)
    if unidade is None:
        raise RecursoNaoEncontradoError("Unidade nao encontrada.")
    if cliente_id is not None and db.session.get(Cliente, cliente_id) is None:
        raise RecursoNaoEncontradoError("Cliente nao encontrado.")

    linhas = []
    agregados = {}
    for item in itens:
        produto_id, quantidade, obs = _validar_item(item)
        produto = db.session.get(Produto, produto_id)
        if produto is None:
            raise RecursoNaoEncontradoError("Produto nao encontrado.")
        if not produto.ativo:
            raise ValidacaoError("Produto inativo.")
        linhas.append((produto, quantidade, obs))
        agregados[produto_id] = agregados.get(produto_id, 0) + quantidade

    for produto_id, quantidade in agregados.items():
        estoque = db.session.scalar(
            select(Estoque).filter_by(unidadeId=unidade_id, produtoId=produto_id)
        )
        if estoque is None or estoque.quantidadeAtual < quantidade:
            raise EstoqueInsuficienteError("Estoque insuficiente para um dos produtos.")

    pedido = Pedido(
        unidadeId=unidade_id,
        clienteId=cliente_id,
        usuarioId=usuario_id,
        canalPedido=canal_pedido,
        status="RECEBIDO",
        valorProdutos=Decimal("0.00"),
        valorDesconto=Decimal("0.00"),
        valorTotal=Decimal("0.00"),
        observacao=observacao,
    )
    db.session.add(pedido)
    db.session.flush()

    valor_produtos = Decimal("0.00")
    itens_desconto = []
    for produto, quantidade, obs in linhas:
        valor_unitario = produto.precoBase
        valor_total_item = valor_unitario * quantidade
        valor_produtos += valor_total_item
        itens_desconto.append((produto.id, valor_total_item))
        db.session.add(
            ItemPedido(
                pedidoId=pedido.id,
                produtoId=produto.id,
                quantidade=quantidade,
                valorUnitario=valor_unitario,
                valorTotalItem=valor_total_item,
                observacao=obs,
            )
        )

    valor_desconto = calcular_desconto(itens_desconto)
    if valor_desconto > valor_produtos:
        valor_desconto = valor_produtos

    pedido.valorProdutos = valor_produtos
    pedido.valorDesconto = valor_desconto
    pedido.valorTotal = valor_produtos - valor_desconto

    for produto_id, quantidade in agregados.items():
        estoque = db.session.scalar(
            select(Estoque).filter_by(unidadeId=unidade_id, produtoId=produto_id)
        )
        resultado = db.session.execute(
            update(Estoque)
            .where(
                Estoque.id == estoque.id,
                Estoque.quantidadeAtual >= quantidade,
            )
            .values(quantidadeAtual=Estoque.quantidadeAtual - quantidade)
        )
        if resultado.rowcount == 0:
            db.session.rollback()
            raise EstoqueInsuficienteError("Estoque insuficiente para um dos produtos.")
        db.session.add(
            MovimentacaoEstoque(
                estoqueId=estoque.id,
                tipo="SAIDA",
                quantidade=quantidade,
                motivo="Venda - pedido",
                pedidoId=pedido.id,
                usuarioId=usuario_id,
            )
        )

    registrar_auditoria(
        usuario_id,
        "Pedido",
        pedido.id,
        "CRIACAO",
        dados_novos={
            "unidadeId": unidade_id,
            "canalPedido": canal_pedido,
            "clienteId": cliente_id,
            "status": "RECEBIDO",
            "valorTotal": str(pedido.valorTotal),
        },
        ip=ip,
    )
    _registrar_historico(pedido.id, None, "RECEBIDO", usuario_id, "Pedido criado")

    db.session.commit()
    return pedido


def alterar_status(pedido_id, novo_status, usuario_id=None, observacao=None, ip=None):
    pedido = db.session.get(Pedido, pedido_id)
    if pedido is None:
        raise RecursoNaoEncontradoError("Pedido nao encontrado.")
    if novo_status not in STATUS_PEDIDO:
        raise ValidacaoError("Status invalido.")
    if novo_status == "CANCELADO":
        raise TransicaoStatusInvalidaError(
            "Use a operacao de cancelamento para cancelar o pedido."
        )

    atual = pedido.status
    if atual not in TRANSICOES_PERMITIDAS or not TRANSICOES_PERMITIDAS[atual]:
        raise TransicaoStatusInvalidaError("Pedido nao pode mais ser alterado.")
    if novo_status not in TRANSICOES_PERMITIDAS[atual]:
        raise TransicaoStatusInvalidaError("Transicao de status invalida.")

    pedido.status = novo_status
    registrar_auditoria(
        usuario_id,
        "Pedido",
        pedido.id,
        "ALTERACAO_STATUS",
        dados_anteriores={"status": atual},
        dados_novos={"status": novo_status},
        ip=ip,
    )
    _registrar_historico(pedido.id, atual, novo_status, usuario_id, observacao)
    db.session.commit()
    return pedido


def _devolver_estoque(unidade_id, produto_id, quantidade, pedido_id, usuario_id):
    estoque = db.session.scalar(
        select(Estoque).filter_by(unidadeId=unidade_id, produtoId=produto_id)
    )
    if estoque is None:
        estoque = Estoque(
            unidadeId=unidade_id,
            produtoId=produto_id,
            quantidadeAtual=0,
            quantidadeMinima=0,
        )
        db.session.add(estoque)
        db.session.flush()
    db.session.execute(
        update(Estoque)
        .where(Estoque.id == estoque.id)
        .values(quantidadeAtual=Estoque.quantidadeAtual + quantidade)
    )
    db.session.add(
        MovimentacaoEstoque(
            estoqueId=estoque.id,
            tipo="ENTRADA",
            quantidade=quantidade,
            motivo="Cancelamento do pedido",
            pedidoId=pedido_id,
            usuarioId=usuario_id,
        )
    )


def cancelar_pedido(pedido_id, usuario_id=None, observacao=None, ip=None):
    pedido = db.session.get(Pedido, pedido_id)
    if pedido is None:
        raise RecursoNaoEncontradoError("Pedido nao encontrado.")

    atual = pedido.status
    if atual not in STATUS_CANCELAVEIS:
        raise TransicaoStatusInvalidaError(
            "Pedido nao pode ser cancelado no status atual."
        )

    itens = db.session.scalars(
        select(ItemPedido).where(ItemPedido.pedidoId == pedido.id)
    ).all()
    for item in itens:
        _devolver_estoque(
            pedido.unidadeId, item.produtoId, item.quantidade, pedido.id, usuario_id
        )

    pedido.status = "CANCELADO"
    estornar_pontos_por_pedido(pedido, usuario_id, ip=ip)
    registrar_auditoria(
        usuario_id,
        "Pedido",
        pedido.id,
        "CANCELAMENTO",
        dados_anteriores={"status": atual},
        dados_novos={"status": "CANCELADO"},
        ip=ip,
    )
    _registrar_historico(pedido.id, atual, "CANCELADO", usuario_id, observacao)
    db.session.commit()
    return pedido
