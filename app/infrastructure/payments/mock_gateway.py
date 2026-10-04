import itertools
import time

from app.application.interfaces.gateway_pagamento import (
    GatewayPagamento,
    RespostaPagamento,
)

_contador = itertools.count(1)

RESULTADOS_SIMULAVEIS = ("APROVADO", "RECUSADO")


class MockGatewayPagamento(GatewayPagamento):
    """Gateway de pagamento simulado, sem integracao real.

    O resultado e deterministico: por padrao aprova, e pode ser forçado a
    recusar via `simular_resultado="RECUSADO"` (campo de desenvolvimento).
    Pagamento em DINHEIRO nao passa por gateway externo e e sempre aprovado.
    """

    PROVEDOR = "MockGateway"

    def solicitar_pagamento(self, pedido_id, valor, metodo, simular_resultado=None):
        if metodo == "DINHEIRO":
            status = "APROVADO"
            mensagem = "Pagamento em dinheiro registrado (mock, sem gateway externo)."
        else:
            status = simular_resultado or "APROVADO"
            if status not in RESULTADOS_SIMULAVEIS:
                status = "APROVADO"
            if status == "APROVADO":
                mensagem = "Pagamento aprovado pelo gateway simulado."
            else:
                mensagem = "Pagamento recusado pelo gateway simulado."

        identificador = (
            f"MOCK-{metodo}-{pedido_id}-{int(time.time() * 1000)}-{next(_contador)}"
        )
        return RespostaPagamento(
            status=status,
            idTransacaoExterna=identificador,
            provedor=self.PROVEDOR,
            mensagem=mensagem,
        )
