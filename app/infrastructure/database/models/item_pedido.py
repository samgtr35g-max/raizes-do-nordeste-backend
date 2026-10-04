from app.infrastructure.database import db


class ItemPedido(db.Model):
    __tablename__ = "itens_pedido"
    __table_args__ = (
        db.CheckConstraint(
            "quantidade > 0",
            name="ck_item_pedido_quantidade_positiva",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    pedidoId = db.Column(
        db.Integer,
        db.ForeignKey("pedidos.id"),
        nullable=False,
    )
    produtoId = db.Column(
        db.Integer,
        db.ForeignKey("produtos.id"),
        nullable=False,
    )
    quantidade = db.Column(db.Integer, nullable=False)
    valorUnitario = db.Column(db.Numeric(10, 2), nullable=False)
    valorTotalItem = db.Column(db.Numeric(10, 2), nullable=False)
    observacao = db.Column(db.String(255))

    pedido = db.relationship("Pedido", back_populates="itens")
    produto = db.relationship("Produto", backref="itens_pedido")

    def __repr__(self):
        return f"<ItemPedido id={self.id} pedidoId={self.pedidoId}>"
