from app.infrastructure.database import db


class UsuarioPapel(db.Model):
    __tablename__ = "usuarios_papeis"

    usuarioId = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        primary_key=True,
    )
    papelId = db.Column(
        db.Integer,
        db.ForeignKey("papeis.id"),
        primary_key=True,
    )
    atribuidoEm = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now(),
    )

    def __repr__(self):
        return f"<UsuarioPapel usuarioId={self.usuarioId} papelId={self.papelId}>"
