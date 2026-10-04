from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.request_utils import obter_ip
from app.api.routes.guards import exigir_permissao
from app.api.routes.pagamentos import serializar_pagamento
from app.api.routes.scope import garantir_escopo as _garantir_escopo
from app.api.routes.scope import id_opcional, resolver_unidade
from app.application.use_cases.pagamentos import listar_pagamentos_do_pedido
from app.application.use_cases.pedidos import (
    alterar_status,
    cancelar_pedido,
    criar_pedido,
    listar_pedidos,
    obter_pedido,
)
from app.domain.exceptions import ValidacaoError
from app.infrastructure.database import db
from app.infrastructure.database.models import Usuario
from app.infrastructure.database.models.pedido import CANAL_PEDIDO, STATUS_PEDIDO

pedidos_bp = Blueprint("pedidos", __name__, url_prefix="/pedidos")


def _usuario_atual():
    return db.session.get(Usuario, int(get_jwt_identity()))


def _serializar_item(item):
    return {
        "id": item.id,
        "produtoId": item.produtoId,
        "quantidade": item.quantidade,
        "valorUnitario": str(item.valorUnitario),
        "valorTotalItem": str(item.valorTotalItem),
        "observacao": item.observacao,
    }


def _serializar_pedido(pedido, incluir_detalhes=False):
    dados = {
        "id": pedido.id,
        "unidadeId": pedido.unidadeId,
        "clienteId": pedido.clienteId,
        "usuarioId": pedido.usuarioId,
        "canalPedido": pedido.canalPedido,
        "status": pedido.status,
        "valorProdutos": str(pedido.valorProdutos),
        "valorDesconto": str(pedido.valorDesconto),
        "valorTotal": str(pedido.valorTotal),
        "observacao": pedido.observacao,
        "criadoEm": pedido.criadoEm.isoformat() if pedido.criadoEm else None,
    }
    if incluir_detalhes:
        dados["itens"] = [_serializar_item(item) for item in pedido.itens]
        dados["historico"] = [
            {
                "statusAnterior": h.statusAnterior,
                "statusNovo": h.statusNovo,
                "observacao": h.observacao,
                "usuarioId": h.usuarioId,
                "criadoEm": h.criadoEm.isoformat() if h.criadoEm else None,
            }
            for h in pedido.historico
        ]
    return dados


@pedidos_bp.post("")
@jwt_required()
def criar():
    usuario = _usuario_atual()
    dados = request.get_json(silent=True) or {}
    unidade_id = resolver_unidade(
        usuario, id_opcional(dados.get("unidadeId"), "unidadeId"), obrigatorio=True
    )

    pedido = criar_pedido(
        unidade_id=unidade_id,
        canal_pedido=dados.get("canalPedido"),
        itens=dados.get("itens"),
        cliente_id=id_opcional(dados.get("clienteId"), "clienteId"),
        usuario_id=usuario.id,
        observacao=dados.get("observacao"),
        ip=obter_ip(request),
    )
    return jsonify(_serializar_pedido(pedido, incluir_detalhes=True)), 201


@pedidos_bp.get("")
@jwt_required()
def listar():
    usuario = _usuario_atual()
    canal = request.args.get("canalPedido")
    status = request.args.get("status")
    if canal is not None and canal not in CANAL_PEDIDO:
        raise ValidacaoError("canalPedido invalido.")
    if status is not None and status not in STATUS_PEDIDO:
        raise ValidacaoError("status invalido.")

    unidade_id = resolver_unidade(
        usuario, request.args.get("unidadeId", type=int), obrigatorio=False
    )
    pedidos = listar_pedidos(
        unidade_id=unidade_id, canal_pedido=canal, status=status
    )
    return jsonify([_serializar_pedido(pedido) for pedido in pedidos]), 200


@pedidos_bp.get("/<int:pedido_id>")
@jwt_required()
def obter(pedido_id):
    usuario = _usuario_atual()
    pedido = obter_pedido(pedido_id)
    _garantir_escopo(usuario, pedido.unidadeId)
    return jsonify(_serializar_pedido(pedido, incluir_detalhes=True)), 200


@pedidos_bp.patch("/<int:pedido_id>/status")
@exigir_permissao("PEDIDO_CANCELAR")
def mudar_status(pedido_id):
    usuario = _usuario_atual()
    dados = request.get_json(silent=True) or {}
    pedido = obter_pedido(pedido_id)
    _garantir_escopo(usuario, pedido.unidadeId)
    pedido = alterar_status(
        pedido_id,
        dados.get("status"),
        usuario_id=usuario.id,
        observacao=dados.get("observacao"),
        ip=obter_ip(request),
    )
    return jsonify(_serializar_pedido(pedido, incluir_detalhes=True)), 200


@pedidos_bp.post("/<int:pedido_id>/cancelamento")
@exigir_permissao("PEDIDO_CANCELAR")
def cancelar(pedido_id):
    usuario = _usuario_atual()
    dados = request.get_json(silent=True) or {}
    pedido = obter_pedido(pedido_id)
    _garantir_escopo(usuario, pedido.unidadeId)
    pedido = cancelar_pedido(
        pedido_id,
        usuario_id=usuario.id,
        observacao=dados.get("observacao"),
        ip=obter_ip(request),
    )
    return jsonify(_serializar_pedido(pedido, incluir_detalhes=True)), 200


@pedidos_bp.get("/<int:pedido_id>/pagamentos")
@jwt_required()
def pagamentos_do_pedido(pedido_id):
    usuario = _usuario_atual()
    pedido = obter_pedido(pedido_id)
    _garantir_escopo(usuario, pedido.unidadeId)
    pagamentos = listar_pagamentos_do_pedido(pedido_id)
    return jsonify([serializar_pagamento(p) for p in pagamentos]), 200
