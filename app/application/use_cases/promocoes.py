from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select

from app.infrastructure.database import db
from app.infrastructure.database.models import Promocao

CENTAVO = Decimal("0.01")


def _desconto_da_promocao(promocao, subtotal):
    if promocao.tipoDesconto == "PERCENTUAL":
        desconto = subtotal * promocao.valor / Decimal("100")
    else:
        desconto = promocao.valor
    desconto = desconto.quantize(CENTAVO, rounding=ROUND_HALF_UP)
    if desconto < Decimal("0.00"):
        desconto = Decimal("0.00")
    if desconto > subtotal:
        desconto = subtotal
    return desconto


def calcular_desconto(itens, data_ref=None):
    """Calcula o desconto do pedido.

    `itens` e uma lista de tuplas (produtoId, subtotal). Para cada item,
    escolhe a promocao que gera o MAIOR beneficio (sem acumular). Promocoes
    gerais (produtoId nulo) valem para qualquer item.
    """
    if data_ref is None:
        data_ref = date.today()

    promocoes = db.session.scalars(
        select(Promocao).where(
            Promocao.ativa.is_(True),
            Promocao.dataInicio <= data_ref,
            Promocao.dataFim >= data_ref,
        )
    ).all()

    total = Decimal("0.00")
    for produto_id, subtotal in itens:
        melhor = Decimal("0.00")
        for promocao in promocoes:
            if promocao.produtoId is not None and promocao.produtoId != produto_id:
                continue
            desconto = _desconto_da_promocao(promocao, subtotal)
            if desconto > melhor:
                melhor = desconto
        total += melhor
    return total
