import json

from sqlalchemy import select

from app.domain.exceptions import (
    PagamentoDuplicadoError,
    PagamentoNaoPermitidoError,
    RecursoNaoEncontradoError,
    ValidacaoError,
)
from app.application.use_cases.fidelidade import acumular_pontos_por_pedido
from app.infrastructure.audit.auditoria import registrar_auditoria
from app.infrastructure.database import db
from app.infrastructure.database.models import Pagamento, Pedido
from app.infrastructure.database.models.pagamento import METODO_PAGAMENTO
from app.infrastructure.payments.mock_gateway import MockGatewayPagamento

STATUS_NAO_PAGAVEIS = {"CANCELADO", "CONCLUIDO"}


def _gateway_padrao():
    return MockGatewayPagamento()


def _persistir_pagamento(pagamento):
    db.session.add(pagamento)
    db.session.flush()


def _confirmar():
    db.session.commit()


def criar_pagamento(pedido_id, metodo, usuario_id=None, simular_resultado=None, gateway=None, ip=None):
    if metodo not in METODO_PAGAMENTO:
        raise ValidacaoError("Metodo de pagamento invalido.")

    pedido = db.session.get(Pedido, pedido_id)
    if pedido is None:
        raise RecursoNaoEncontradoError("Pedido nao encontrado.")

    if pedido.status in STATUS_NAO_PAGAVEIS:
        raise PagamentoNaoPermitidoError(
            f"Pedido nao pode ser pago no status {pedido.status}."
        )

    aprovado = db.session.scalar(
        select(Pagamento).where(
            Pagamento.pedidoId == pedido_id,
            Pagamento.status == "APROVADO",
        )
    )
    if aprovado is not None:
        raise PagamentoDuplicadoError()

    valor = pedido.valorTotal

    gateway = gateway or _gateway_padrao()
    resposta = gateway.solicitar_pagamento(pedido.id, valor, metodo, simular_resultado)

    pagamento = Pagamento(
        pedidoId=pedido.id,
        valor=valor,
        metodo=metodo,
        status=resposta.status,
        provedor=resposta.provedor,
        idTransacaoExterna=resposta.idTransacaoExterna,
        payloadResposta=json.dumps(resposta.para_dict(), ensure_ascii=False),
    )
    _persistir_pagamento(pagamento)
    if pagamento.status == "APROVADO":
        acumular_pontos_por_pedido(pedido, usuario_id)
    registrar_auditoria(
        usuario_id,
        "Pagamento",
        pagamento.id,
        "PAGAMENTO_APROVADO" if pagamento.status == "APROVADO" else "PAGAMENTO_RECUSADO",
        dados_novos={
            "pedidoId": pedido.id,
            "status": pagamento.status,
            "valor": str(pagamento.valor),
            "provedor": pagamento.provedor,
            "idTransacaoExterna": pagamento.idTransacaoExterna,
        },
        ip=ip,
    )
    _confirmar()
    return pagamento


def obter_pagamento(pagamento_id):
    pagamento = db.session.get(Pagamento, pagamento_id)
    if pagamento is None:
        raise RecursoNaoEncontradoError("Pagamento nao encontrado.")
    return pagamento


def listar_pagamentos_do_pedido(pedido_id):
    pedido = db.session.get(Pedido, pedido_id)
    if pedido is None:
        raise RecursoNaoEncontradoError("Pedido nao encontrado.")
    return db.session.scalars(
        select(Pagamento)
        .where(Pagamento.pedidoId == pedido_id)
        .order_by(Pagamento.id)
    ).all()
