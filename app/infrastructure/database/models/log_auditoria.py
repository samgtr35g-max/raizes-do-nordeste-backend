from app.infrastructure.database import db


class LogAuditoria(db.Model):
    __tablename__ = "logs_auditoria"

    id = db.Column(db.Integer, primary_key=True)
    usuarioId = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True,
    )
    entidade = db.Column(db.String(120), nullable=False)
    entidadeId = db.Column(db.Integer, nullable=True)
    acao = db.Column(db.String(30), nullable=False)
    dadosAnteriores = db.Column(db.JSON, nullable=True)
    dadosNovos = db.Column(db.JSON, nullable=True)
    ip = db.Column(db.String(45), nullable=True)
    criadoEm = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    usuario = db.relationship("Usuario", back_populates="logsAuditoria")

    def __repr__(self):
        return f"<LogAuditoria id={self.id} entidade={self.entidade!r} acao={self.acao!r}>"
