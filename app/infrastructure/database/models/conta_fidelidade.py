from app.infrastructure.database import db


class ContaFidelidade(db.Model):
    __tablename__ = "contas_fidelidade"
    __table_args__ = (
        db.CheckConstraint(
            "saldoPontos >= 0",
            name="ck_conta_fidelidade_saldo_nao_negativo",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    clienteId = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id"),
        unique=True,
        nullable=False,
    )
    saldoPontos = db.Column(db.Integer, nullable=False, default=0)
    atualizadoEm = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    cliente = db.relationship("Cliente", back_populates="contaFidelidade")
    movimentacoes = db.relationship(
        "MovimentacaoPontos",
        back_populates="contaFidelidade",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<ContaFidelidade id={self.id} clienteId={self.clienteId} saldo={self.saldoPontos}>"
