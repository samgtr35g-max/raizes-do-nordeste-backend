from app.infrastructure.database import db


class MovimentacaoEstoque(db.Model):
    __tablename__ = "movimentacoes_estoque"
    __table_args__ = (
        db.CheckConstraint(
            "quantidade > 0",
            name="ck_movimentacao_quantidade_positiva",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    estoqueId = db.Column(
        db.Integer,
        db.ForeignKey("estoques.id"),
        nullable=False,
    )
    tipo = db.Column(
        db.Enum("ENTRADA", "SAIDA", "AJUSTE", name="tipo_movimentacao_estoque"),
        nullable=False,
    )
    quantidade = db.Column(db.Integer, nullable=False)
    motivo = db.Column(db.String(255))
    pedidoId = db.Column(
        db.Integer,
        db.ForeignKey("pedidos.id"),
        nullable=True,
    )
    usuarioId = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
    )
    criadoEm = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now(),
    )

    estoque = db.relationship("Estoque", backref="movimentacoes")

    def __repr__(self):
        return f"<MovimentacaoEstoque id={self.id} tipo={self.tipo!r}>"
