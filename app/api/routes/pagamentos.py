from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.request_utils import obter_ip
from app.api.routes.scope import garantir_escopo, id_opcional
from app.application.use_cases.pagamentos import criar_pagamento, obter_pagamento
from app.domain.exceptions import RecursoNaoEncontradoError, ValidacaoError
from app.infrastructure.database import db
from app.infrastructure.database.models import Pedido, Usuario
from app.infrastructure.payments.mock_gateway import RESULTADOS_SIMULAVEIS

pagamentos_bp = Blueprint("pagamentos", __name__, url_prefix="/pagamentos")


def _usuario_atual():
    return db.session.get(Usuario, int(get_jwt_identity()))


def serializar_pagamento(pagamento):
    return {
        "id": pagamento.id,
        "pedidoId": pagamento.pedidoId,
        "valor": str(pagamento.valor),
        "metodo": pagamento.metodo,
        "status": pagamento.status,
        "provedor": pagamento.provedor,
        "idTransacaoExterna": pagamento.idTransacaoExterna,
        "payloadResposta": pagamento.payloadResposta,
        "criadoEm": pagamento.criadoEm.isoformat() if pagamento.criadoEm else None,
        "atualizadoEm": (
            pagamento.atualizadoEm.isoformat() if pagamento.atualizadoEm else None
        ),
    }


@pagamentos_bp.post("")
@jwt_required()
def criar():
    usuario = _usuario_atual()
    dados = request.get_json(silent=True) or {}

    pedido_id = id_opcional(dados.get("pedidoId"), "pedidoId")
    if pedido_id is None:
        raise ValidacaoError("Informe o pedido.")

    pedido = db.session.get(Pedido, pedido_id)
    if pedido is None:
        raise RecursoNaoEncontradoError("Pedido nao encontrado.")
    garantir_escopo(usuario, pedido.unidadeId)

    simular = dados.get("simularResultado")
    if simular is not None and simular not in RESULTADOS_SIMULAVEIS:
        raise ValidacaoError("simularResultado invalido.")

    pagamento = criar_pagamento(
        pedido_id,
        dados.get("metodo"),
        usuario_id=usuario.id,
        simular_resultado=simular,
        ip=obter_ip(request),
    )
    return jsonify(serializar_pagamento(pagamento)), 201


@pagamentos_bp.get("/<int:pagamento_id>")
@jwt_required()
def obter(pagamento_id):
    usuario = _usuario_atual()
    pagamento = obter_pagamento(pagamento_id)
    pedido = db.session.get(Pedido, pagamento.pedidoId)
    garantir_escopo(usuario, pedido.unidadeId)
    return jsonify(serializar_pagamento(pagamento)), 200
