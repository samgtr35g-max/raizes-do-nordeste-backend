from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import select

from app.api.request_utils import obter_ip
from app.application.use_cases.fidelidade import (
    anonimizar_cliente,
    obter_conta_com_historico,
    resgatar_pontos,
)
from app.domain.exceptions import AcessoNegadoError, RecursoNaoEncontradoError
from app.infrastructure.database import db
from app.infrastructure.database.models import Cliente, Usuario, UsuarioPapel

fidelidade_bp = Blueprint("fidelidade", __name__, url_prefix="/clientes")


def _usuario_atual():
    return db.session.get(Usuario, int(get_jwt_identity()))


def _autorizar(usuario, cliente):
    if cliente.usuarioId is not None and cliente.usuarioId == usuario.id:
        return
    eh_interno = db.session.scalar(
        select(UsuarioPapel).filter_by(usuarioId=usuario.id)
    )
    if eh_interno is not None:
        return
    raise AcessoNegadoError("Voce nao tem acesso a este cliente.")


def _carregar_cliente(cliente_id):
    cliente = db.session.get(Cliente, cliente_id)
    if cliente is None:
        raise RecursoNaoEncontradoError("Cliente nao encontrado.")
    return cliente


def _serializar_movimentacao(mov):
    return {
        "id": mov.id,
        "tipo": mov.tipo,
        "pontos": mov.pontos,
        "pedidoId": mov.pedidoId,
        "criadoEm": mov.criadoEm.isoformat() if mov.criadoEm else None,
    }


@fidelidade_bp.get("/<int:cliente_id>/fidelidade")
@jwt_required()
def consultar(cliente_id):
    usuario = _usuario_atual()
    cliente = _carregar_cliente(cliente_id)
    _autorizar(usuario, cliente)

    cliente, conta, movimentacoes = obter_conta_com_historico(cliente_id)
    return jsonify(
        {
            "cliente": {"id": cliente.id, "nome": cliente.nome},
            "saldoPontos": conta.saldoPontos,
            "movimentacoes": [_serializar_movimentacao(m) for m in movimentacoes],
        }
    ), 200


@fidelidade_bp.post("/<int:cliente_id>/fidelidade/resgate")
@jwt_required()
def resgatar(cliente_id):
    usuario = _usuario_atual()
    cliente = _carregar_cliente(cliente_id)
    _autorizar(usuario, cliente)

    dados = request.get_json(silent=True) or {}
    conta, movimentacao = resgatar_pontos(
        cliente_id, dados.get("pontos"), usuario_id=usuario.id, ip=obter_ip(request)
    )
    return jsonify(
        {
            "saldoPontos": conta.saldoPontos,
            "movimentacao": _serializar_movimentacao(movimentacao),
        }
    ), 201


@fidelidade_bp.post("/<int:cliente_id>/anonimizacao")
@jwt_required()
def anonimizar(cliente_id):
    usuario = _usuario_atual()
    cliente = _carregar_cliente(cliente_id)
    _autorizar(usuario, cliente)
    cliente = anonimizar_cliente(cliente_id, usuario_id=usuario.id, ip=obter_ip(request))
    return jsonify(
        {
            "id": cliente.id,
            "nome": cliente.nome,
            "anonimizado": cliente.anonimizado,
        }
    ), 200
