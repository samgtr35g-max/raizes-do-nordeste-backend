from app.infrastructure.database import db


class Permissao(db.Model):
    __tablename__ = "permissoes"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(80), unique=True, nullable=False)
    descricao = db.Column(db.String(255))

    def __repr__(self):
        return f"<Permissao id={self.id} codigo={self.codigo!r}>"
