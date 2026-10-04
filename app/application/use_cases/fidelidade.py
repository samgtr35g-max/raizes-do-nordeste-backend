from sqlalchemy import select

from app.domain.exceptions import (
    RecursoNaoEncontradoError,
    SaldoInsuficienteError,
    ValidacaoError,
)
from app.infrastructure.audit.auditoria import registrar_auditoria
from app.infrastructure.database import db
from app.infrastructure.database.models import (
    Cliente,
    ContaFidelidade,
    MovimentacaoPontos,
)

PONTOS_POR_REAL = 1


def calcular_pontos(valor_total) -> int:
    if valor_total is None or valor_total <= 0:
        return 0
    return int(valor_total // PONTOS_POR_REAL)


def obter_ou_criar_conta(cliente_id):
    cliente = db.session.get(Cliente, cliente_id)
    if cliente is None:
        raise RecursoNaoEncontradoError("Cliente nao encontrado.")
    conta = db.session.scalar(
        select(ContaFidelidade).filter_by(clienteId=cliente_id)
    )
    if conta is None:
        conta = ContaFidelidade(clienteId=cliente_id, saldoPontos=0)
        db.session.add(conta)
        db.session.flush()
    return conta


def _movimentacao_existente(pedido_id, tipo):
    return db.session.scalar(
        select(MovimentacaoPontos).where(
            MovimentacaoPontos.pedidoId == pedido_id,
            MovimentacaoPontos.tipo == tipo,
        )
    )


def acumular_pontos_por_pedido(pedido, usuario_id=None):
    if pedido is None or pedido.clienteId is None:
        return None
    if _movimentacao_existente(pedido.id, "ACUMULO") is not None:
        return None

    pontos = calcular_pontos(pedido.valorTotal)
    if pontos <= 0:
        return None

    conta = obter_ou_criar_conta(pedido.clienteId)
    conta.saldoPontos += pontos
    movimentacao = MovimentacaoPontos(
        contaFidelidadeId=conta.id,
        tipo="ACUMULO",
        pontos=pontos,
        pedidoId=pedido.id,
    )
    db.session.add(movimentacao)
    return movimentacao


def estornar_pontos_por_pedido(pedido, usuario_id=None, ip=None):
    if pedido is None:
        return None

    acumulo = _movimentacao_existente(pedido.id, "ACUMULO")
    if acumulo is None:
        return None
    if _movimentacao_existente(pedido.id, "ESTORNO") is not None:
        return None

    conta = db.session.get(ContaFidelidade, acumulo.contaFidelidadeId)
    if conta is None:
        return None

    estorno = min(acumulo.pontos, conta.saldoPontos)
    if estorno <= 0:
        return None

    conta.saldoPontos -= estorno
    movimentacao = MovimentacaoPontos(
        contaFidelidadeId=conta.id,
        tipo="ESTORNO",
        pontos=estorno,
        pedidoId=pedido.id,
    )
    db.session.add(movimentacao)
    registrar_auditoria(
        usuario_id,
        "ContaFidelidade",
        conta.id,
        "ESTORNO_PONTOS",
        dados_anteriores={"saldoPontos": conta.saldoPontos + estorno},
        dados_novos={"saldoPontos": conta.saldoPontos, "pontosEstornados": estorno},
        ip=ip,
    )
    return movimentacao


def resgatar_pontos(cliente_id, pontos, usuario_id=None, ip=None):
    if isinstance(pontos, bool) or not isinstance(pontos, int):
        raise ValidacaoError("A quantidade de pontos deve ser um numero inteiro.")
    if pontos <= 0:
        raise ValidacaoError("A quantidade de pontos deve ser maior que zero.")

    conta = obter_ou_criar_conta(cliente_id)
    if conta.saldoPontos < pontos:
        raise SaldoInsuficienteError("Saldo de pontos insuficiente.")

    saldo_anterior = conta.saldoPontos
    conta.saldoPontos -= pontos
    movimentacao = MovimentacaoPontos(
        contaFidelidadeId=conta.id,
        tipo="RESGATE",
        pontos=pontos,
    )
    db.session.add(movimentacao)
    registrar_auditoria(
        usuario_id,
        "ContaFidelidade",
        conta.id,
        "RESGATE_PONTOS",
        dados_anteriores={"saldoPontos": saldo_anterior},
        dados_novos={"saldoPontos": conta.saldoPontos, "pontosResgatados": pontos},
        ip=ip,
    )
    db.session.commit()
    return conta, movimentacao


def anonimizar_cliente(cliente_id, usuario_id=None, ip=None):
    cliente = db.session.get(Cliente, cliente_id)
    if cliente is None:
        raise RecursoNaoEncontradoError("Cliente nao encontrado.")

    cliente.nome = "ANONIMIZADO"
    cliente.cpf = None
    cliente.email = None
    cliente.telefone = None
    cliente.dataNascimento = None
    cliente.aceitaComunicacoes = False
    cliente.anonimizado = True

    registrar_auditoria(
        usuario_id,
        "Cliente",
        cliente.id,
        "ANONIMIZACAO",
        dados_anteriores={"anonimizado": False},
        dados_novos={"anonimizado": True, "resultado": "dados_pessoais_removidos"},
        ip=ip,
    )
    db.session.commit()
    return cliente


def obter_conta_com_historico(cliente_id):
    cliente = db.session.get(Cliente, cliente_id)
    if cliente is None:
        raise RecursoNaoEncontradoError("Cliente nao encontrado.")
    conta = obter_ou_criar_conta(cliente_id)
    db.session.commit()
    movimentacoes = db.session.scalars(
        select(MovimentacaoPontos)
        .where(MovimentacaoPontos.contaFidelidadeId == conta.id)
        .order_by(MovimentacaoPontos.id)
    ).all()
    return cliente, conta, movimentacoes
