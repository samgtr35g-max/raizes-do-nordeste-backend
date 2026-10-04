from app.infrastructure.database import db

TIPO_DESCONTO = ("PERCENTUAL", "VALOR_FIXO")


class Promocao(db.Model):
    __tablename__ = "promocoes"
    __table_args__ = (
        db.CheckConstraint(
            "valor > 0",
            name="ck_promocao_valor_positivo",
        ),
        db.CheckConstraint(
            "dataFim >= dataInicio",
            name="ck_promocao_periodo_valido",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    descricao = db.Column(db.String(255))
    tipoDesconto = db.Column(
        db.Enum(*TIPO_DESCONTO, name="tipo_desconto"),
        nullable=False,
    )
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    dataInicio = db.Column(db.Date, nullable=False)
    dataFim = db.Column(db.Date, nullable=False)
    ativa = db.Column(db.Boolean, nullable=False, default=True)
    produtoId = db.Column(
        db.Integer,
        db.ForeignKey("produtos.id"),
        nullable=True,
    )

    produto = db.relationship("Produto", back_populates="promocoes")

    def __repr__(self):
        return f"<Promocao id={self.id} nome={self.nome!r} ativa={self.ativa}>"
