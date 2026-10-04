from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.request_utils import obter_ip
from app.api.routes.guards import exigir_permissao
from app.api.routes.scope import (
    id_opcional as _id_opcional,
    resolver_unidade as _resolver_unidade,
)
from app.application.use_cases.estoque import (
    consultar_estoque,
    registrar_ajuste,
    registrar_entrada,
    registrar_saida,
)
from app.domain.exceptions import ValidacaoError
from app.infrastructure.database import db
from app.infrastructure.database.models import Usuario

estoque_bp = Blueprint("estoque", __name__, url_prefix="/estoque")


def _usuario_atual():
    return db.session.get(Usuario, int(get_jwt_identity()))


def _serializar_estoque(estoque):
    return {
        "id": estoque.id,
        "unidadeId": estoque.unidadeId,
        "produtoId": estoque.produtoId,
        "quantidadeAtual": estoque.quantidadeAtual,
        "quantidadeMinima": estoque.quantidadeMinima,
    }


def _serializar_movimentacao(mov):
    return {
        "id": mov.id,
        "tipo": mov.tipo,
        "quantidade": mov.quantidade,
        "motivo": mov.motivo,
        "pedidoId": mov.pedidoId,
        "usuarioId": mov.usuarioId,
        "criadoEm": mov.criadoEm.isoformat() if mov.criadoEm else None,
    }


@estoque_bp.get("")
@jwt_required()
def listar_estoque():
    usuario = _usuario_atual()
    unidade_param = _id_opcional(request.args.get("unidadeId", type=int), "unidadeId")
    produto_param = _id_opcional(request.args.get("produtoId", type=int), "produtoId")
    unidade_id = _resolver_unidade(usuario, unidade_param, obrigatorio=False)
    itens = consultar_estoque(unidade_id=unidade_id, produto_id=produto_param)
    return jsonify([_serializar_estoque(item) for item in itens]), 200


@estoque_bp.post("/entrada")
@exigir_permissao("ESTOQUE_AJUSTAR")
def post_entrada():
    usuario = _usuario_atual()
    dados = request.get_json(silent=True) or {}
    unidade_id = _resolver_unidade(
        usuario, _id_opcional(dados.get("unidadeId"), "unidadeId"), obrigatorio=True
    )
    produto_id = _id_opcional(dados.get("produtoId"), "produtoId")
    if produto_id is None:
        raise ValidacaoError("Informe o produto.")

    estoque, movimentacao = registrar_entrada(
        unidade_id,
        produto_id,
        dados.get("quantidade"),
        motivo=dados.get("motivo"),
        usuario_id=usuario.id,
        ip=obter_ip(request),
    )
    return jsonify(
        {
            "estoque": _serializar_estoque(estoque),
            "movimentacao": _serializar_movimentacao(movimentacao),
        }
    ), 201


@estoque_bp.post("/saida")
@exigir_permissao("ESTOQUE_AJUSTAR")
def post_saida():
    usuario = _usuario_atual()
    dados = request.get_json(silent=True) or {}
    unidade_id = _resolver_unidade(
        usuario, _id_opcional(dados.get("unidadeId"), "unidadeId"), obrigatorio=True
    )
    produto_id = _id_opcional(dados.get("produtoId"), "produtoId")
    if produto_id is None:
        raise ValidacaoError("Informe o produto.")

    estoque, movimentacao = registrar_saida(
        unidade_id,
        produto_id,
        dados.get("quantidade"),
        motivo=dados.get("motivo"),
        usuario_id=usuario.id,
        ip=obter_ip(request),
    )
    return jsonify(
        {
            "estoque": _serializar_estoque(estoque),
            "movimentacao": _serializar_movimentacao(movimentacao),
        }
    ), 201


@estoque_bp.post("/ajuste")
@exigir_permissao("ESTOQUE_AJUSTAR")
def post_ajuste():
    usuario = _usuario_atual()
    dados = request.get_json(silent=True) or {}
    unidade_id = _resolver_unidade(
        usuario, _id_opcional(dados.get("unidadeId"), "unidadeId"), obrigatorio=True
    )
    produto_id = _id_opcional(dados.get("produtoId"), "produtoId")
    if produto_id is None:
        raise ValidacaoError("Informe o produto.")

    estoque, movimentacao = registrar_ajuste(
        unidade_id,
        produto_id,
        dados.get("quantidade"),
        motivo=dados.get("motivo"),
        usuario_id=usuario.id,
        ip=obter_ip(request),
    )
    return jsonify(
        {
            "estoque": _serializar_estoque(estoque),
            "movimentacao": _serializar_movimentacao(movimentacao),
        }
    ), 201
