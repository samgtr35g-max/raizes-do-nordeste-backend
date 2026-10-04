from app.infrastructure.database import db
from app.infrastructure.database.models.pedido import STATUS_PEDIDO


class HistoricoStatusPedido(db.Model):
    __tablename__ = "historico_status_pedido"

    id = db.Column(db.Integer, primary_key=True)
    pedidoId = db.Column(
        db.Integer,
        db.ForeignKey("pedidos.id"),
        nullable=False,
    )
    statusAnterior = db.Column(
        db.Enum(*STATUS_PEDIDO, name="status_pedido"),
        nullable=True,
    )
    statusNovo = db.Column(
        db.Enum(*STATUS_PEDIDO, name="status_pedido"),
        nullable=False,
    )
    usuarioId = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
    )
    observacao = db.Column(db.String(255))
    criadoEm = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    pedido = db.relationship("Pedido", back_populates="historico")
    usuario = db.relationship("Usuario", backref="historicos_status_pedido")

    def __repr__(self):
        return f"<HistoricoStatusPedido id={self.id} statusNovo={self.statusNovo!r}>"
