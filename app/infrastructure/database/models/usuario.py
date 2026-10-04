from app.infrastructure.database import db


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senhaHash = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    unidadeId = db.Column(db.Integer, db.ForeignKey("unidades.id"), nullable=True)
    criadoEm = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    atualizadoEm = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    unidade = db.relationship("Unidade", backref="usuarios")
    logsAuditoria = db.relationship("LogAuditoria", back_populates="usuario")

    def __repr__(self):
        return f"<Usuario id={self.id} email={self.email!r}>"
