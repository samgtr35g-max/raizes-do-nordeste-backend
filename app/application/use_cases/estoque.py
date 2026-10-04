from sqlalchemy import select, update

from app.domain.exceptions import (
    EstoqueInsuficienteError,
    RecursoNaoEncontradoError,
    ValidacaoError,
)
from app.infrastructure.audit.auditoria import registrar_auditoria
from app.infrastructure.database import db
from app.infrastructure.database.models import (
    Estoque,
    MovimentacaoEstoque,
    Produto,
    Unidade,
)


def consultar_estoque(unidade_id=None, produto_id=None):
    stmt = select(Estoque)
    if unidade_id is not None:
        stmt = stmt.where(Estoque.unidadeId == unidade_id)
    if produto_id is not None:
        stmt = stmt.where(Estoque.produtoId == produto_id)
    return db.session.scalars(stmt).all()


def _validar_quantidade_positiva(quantidade):
    if isinstance(quantidade, bool) or not isinstance(quantidade, int):
        raise ValidacaoError("A quantidade deve ser um numero inteiro.")
    if quantidade <= 0:
        raise ValidacaoError("A quantidade deve ser maior que zero.")


def _validar_quantidade_nao_negativa(quantidade):
    if isinstance(quantidade, bool) or not isinstance(quantidade, int):
        raise ValidacaoError("A quantidade deve ser um numero inteiro.")
    if quantidade < 0:
        raise ValidacaoError("A quantidade nao pode ser negativa.")


def _obter_unidade(unidade_id):
    unidade = db.session.get(Unidade, unidade_id)
    if unidade is None:
        raise RecursoNaoEncontradoError("Unidade nao encontrada.")
    return unidade


def _obter_produto(produto_id):
    produto = db.session.get(Produto, produto_id)
    if produto is None:
        raise RecursoNaoEncontradoError("Produto nao encontrado.")
    return produto


def _obter_estoque(unidade_id, produto_id):
    return db.session.scalar(
        select(Estoque).filter_by(unidadeId=unidade_id, produtoId=produto_id)
    )


def _obter_ou_criar_estoque(unidade_id, produto_id):
    estoque = _obter_estoque(unidade_id, produto_id)
    if estoque is None:
        estoque = Estoque(
            unidadeId=unidade_id,
            produtoId=produto_id,
            quantidadeAtual=0,
            quantidadeMinima=0,
        )
        db.session.add(estoque)
        db.session.flush()
    return estoque


def registrar_entrada(
    unidade_id, produto_id, quantidade, motivo=None, usuario_id=None, pedido_id=None, ip=None
):
    _validar_quantidade_positiva(quantidade)
    _obter_unidade(unidade_id)
    _obter_produto(produto_id)

    estoque = _obter_ou_criar_estoque(unidade_id, produto_id)
    quantidade_anterior = estoque.quantidadeAtual
    db.session.execute(
        update(Estoque)
        .where(Estoque.id == estoque.id)
        .values(quantidadeAtual=Estoque.quantidadeAtual + quantidade)
    )
    movimentacao = MovimentacaoEstoque(
        estoqueId=estoque.id,
        tipo="ENTRADA",
        quantidade=quantidade,
        motivo=motivo,
        usuarioId=usuario_id,
        pedidoId=pedido_id,
    )
    db.session.add(movimentacao)
    registrar_auditoria(
        usuario_id,
        "Estoque",
        estoque.id,
        "ESTOQUE_ENTRADA",
        dados_anteriores={"quantidadeAtual": quantidade_anterior},
        dados_novos={"quantidadeAtual": quantidade_anterior + quantidade},
        ip=ip,
    )
    db.session.commit()
    return estoque, movimentacao


def registrar_saida(
    unidade_id, produto_id, quantidade, motivo=None, usuario_id=None, pedido_id=None, ip=None
):
    _validar_quantidade_positiva(quantidade)
    _obter_unidade(unidade_id)
    _obter_produto(produto_id)

    estoque = _obter_estoque(unidade_id, produto_id)
    if estoque is None:
        raise RecursoNaoEncontradoError(
            "Estoque nao encontrado para esta unidade e produto."
        )

    quantidade_anterior = estoque.quantidadeAtual
    resultado = db.session.execute(
        update(Estoque)
        .where(Estoque.id == estoque.id, Estoque.quantidadeAtual >= quantidade)
        .values(quantidadeAtual=Estoque.quantidadeAtual - quantidade)
    )
    if resultado.rowcount == 0:
        db.session.rollback()
        raise EstoqueInsuficienteError("Saida maior que o estoque disponivel.")

    movimentacao = MovimentacaoEstoque(
        estoqueId=estoque.id,
        tipo="SAIDA",
        quantidade=quantidade,
        motivo=motivo,
        usuarioId=usuario_id,
        pedidoId=pedido_id,
    )
    db.session.add(movimentacao)
    registrar_auditoria(
        usuario_id,
        "Estoque",
        estoque.id,
        "ESTOQUE_SAIDA",
        dados_anteriores={"quantidadeAtual": quantidade_anterior},
        dados_novos={"quantidadeAtual": quantidade_anterior - quantidade},
        ip=ip,
    )
    db.session.commit()
    return estoque, movimentacao


def registrar_ajuste(unidade_id, produto_id, quantidade_nova, motivo=None, usuario_id=None, ip=None):
    _validar_quantidade_nao_negativa(quantidade_nova)
    _obter_unidade(unidade_id)
    _obter_produto(produto_id)

    estoque = _obter_ou_criar_estoque(unidade_id, produto_id)
    quantidade_anterior = estoque.quantidadeAtual
    diferenca = quantidade_nova - quantidade_anterior
    if diferenca == 0:
        raise ValidacaoError("O ajuste nao altera a quantidade atual.")

    db.session.execute(
        update(Estoque)
        .where(Estoque.id == estoque.id)
        .values(quantidadeAtual=quantidade_nova)
    )
    movimentacao = MovimentacaoEstoque(
        estoqueId=estoque.id,
        tipo="AJUSTE",
        quantidade=abs(diferenca),
        motivo=motivo,
        usuarioId=usuario_id,
    )
    db.session.add(movimentacao)
    registrar_auditoria(
        usuario_id,
        "Estoque",
        estoque.id,
        "ESTOQUE_AJUSTE",
        dados_anteriores={"quantidadeAtual": quantidade_anterior},
        dados_novos={"quantidadeAtual": quantidade_nova},
        ip=ip,
    )
    db.session.commit()
    return estoque, movimentacao
