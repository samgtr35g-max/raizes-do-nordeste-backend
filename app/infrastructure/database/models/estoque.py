from app.infrastructure.database import db


class Estoque(db.Model):
    __tablename__ = "estoques"
    __table_args__ = (
        db.UniqueConstraint(
            "unidadeId",
            "produtoId",
            name="uq_estoque_unidade_produto",
        ),
        db.CheckConstraint(
            "quantidadeAtual >= 0",
            name="ck_estoque_quantidade_nao_negativa",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    unidadeId = db.Column(
        db.Integer,
        db.ForeignKey("unidades.id"),
        nullable=False,
    )
    produtoId = db.Column(
        db.Integer,
        db.ForeignKey("produtos.id"),
        nullable=False,
    )
    quantidadeAtual = db.Column(db.Integer, nullable=False, default=0)
    quantidadeMinima = db.Column(db.Integer, nullable=False, default=0)
    atualizadoEm = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    unidade = db.relationship("Unidade", backref="estoques")
    produto = db.relationship("Produto", backref="estoques")

    def __repr__(self):
        return (
            f"<Estoque id={self.id} unidadeId={self.unidadeId} "
            f"produtoId={self.produtoId}>"
        )
