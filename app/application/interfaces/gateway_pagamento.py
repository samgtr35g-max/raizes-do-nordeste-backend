from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class RespostaPagamento:
    status: str
    idTransacaoExterna: str
    provedor: str
    mensagem: str

    def para_dict(self):
        return {
            "status": self.status,
            "idTransacaoExterna": self.idTransacaoExterna,
            "provedor": self.provedor,
            "mensagem": self.mensagem,
        }


class GatewayPagamento(ABC):
    """Contrato de um provedor de pagamento (gateway)."""

    @abstractmethod
    def solicitar_pagamento(
        self,
        pedido_id: int,
        valor,
        metodo: str,
        simular_resultado: str = None,
    ) -> RespostaPagamento:
        """Solicita um pagamento e retorna uma resposta padronizada."""
