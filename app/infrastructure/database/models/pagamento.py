from app.infrastructure.database import db

METODO_PAGAMENTO = ("PIX", "CARTAO", "DINHEIRO")
STATUS_PAGAMENTO = ("PENDENTE", "APROVADO", "RECUSADO", "ESTORNADO")


class Pagamento(db.Model):
    __tablename__ = "pagamentos"
    __table_args__ = (
        db.CheckConstraint(
            "valor >= 0",
            name="ck_pagamento_valor_nao_negativo",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    pedidoId = db.Column(
        db.Integer,
        db.ForeignKey("pedidos.id"),
        nullable=False,
    )
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    metodo = db.Column(
        db.Enum(*METODO_PAGAMENTO, name="metodo_pagamento"),
        nullable=False,
    )
    status = db.Column(
        db.Enum(*STATUS_PAGAMENTO, name="status_pagamento"),
        nullable=False,
        default="PENDENTE",
    )
    provedor = db.Column(db.String(120))
    idTransacaoExterna = db.Column(db.String(120), unique=True, nullable=True)
    payloadResposta = db.Column(db.Text)
    criadoEm = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    atualizadoEm = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    pedido = db.relationship("Pedido", back_populates="pagamentos")

    def __repr__(self):
        return f"<Pagamento id={self.id} status={self.status!r} valor={self.valor}>"
