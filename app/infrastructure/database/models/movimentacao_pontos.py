from app.infrastructure.database import db

TIPO_MOVIMENTACAO_PONTOS = ("ACUMULO", "RESGATE", "ESTORNO", "EXPIRACAO")


class MovimentacaoPontos(db.Model):
    __tablename__ = "movimentacoes_pontos"
    __table_args__ = (
        db.CheckConstraint(
            "pontos > 0",
            name="ck_movimentacao_pontos_positivos",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    contaFidelidadeId = db.Column(
        db.Integer,
        db.ForeignKey("contas_fidelidade.id"),
        nullable=False,
    )
    tipo = db.Column(
        db.Enum(*TIPO_MOVIMENTACAO_PONTOS, name="tipo_movimentacao_pontos"),
        nullable=False,
    )
    pontos = db.Column(db.Integer, nullable=False)
    pedidoId = db.Column(
        db.Integer,
        db.ForeignKey("pedidos.id"),
        nullable=True,
    )
    criadoEm = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    contaFidelidade = db.relationship(
        "ContaFidelidade",
        back_populates="movimentacoes",
    )
    pedido = db.relationship("Pedido", backref="movimentacoes_pontos")

    def __repr__(self):
        return f"<MovimentacaoPontos id={self.id} tipo={self.tipo!r} pontos={self.pontos}>"
