from app.infrastructure.database import db

CANAL_PEDIDO = ("APP", "TOTEM", "BALCAO", "PICKUP", "WEB")
STATUS_PEDIDO = (
    "RECEBIDO",
    "EM_PREPARO",
    "PRONTO",
    "CONCLUIDO",
    "CANCELADO",
)


class Pedido(db.Model):
    __tablename__ = "pedidos"

    id = db.Column(db.Integer, primary_key=True)
    unidadeId = db.Column(
        db.Integer,
        db.ForeignKey("unidades.id"),
        nullable=False,
    )
    clienteId = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id"),
        nullable=True,
    )
    usuarioId = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
    )
    canalPedido = db.Column(
        db.Enum(*CANAL_PEDIDO, name="canal_pedido"),
        nullable=False,
    )
    status = db.Column(
        db.Enum(*STATUS_PEDIDO, name="status_pedido"),
        nullable=False,
        default="RECEBIDO",
    )
    valorProdutos = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    valorDesconto = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    valorTotal = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    observacao = db.Column(db.String(255))
    criadoEm = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    atualizadoEm = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    unidade = db.relationship("Unidade", backref="pedidos")
    cliente = db.relationship("Cliente", backref="pedidos")
    usuario = db.relationship("Usuario", backref="pedidos")
    itens = db.relationship(
        "ItemPedido",
        back_populates="pedido",
        cascade="all, delete-orphan",
    )
    historico = db.relationship(
        "HistoricoStatusPedido",
        back_populates="pedido",
        cascade="all, delete-orphan",
    )
    pagamentos = db.relationship("Pagamento", back_populates="pedido")

    def __repr__(self):
        return f"<Pedido id={self.id} canal={self.canalPedido!r} status={self.status!r}>"
