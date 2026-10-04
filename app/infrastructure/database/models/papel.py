from app.infrastructure.database import db


class Papel(db.Model):
    __tablename__ = "papeis"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), unique=True, nullable=False)
    descricao = db.Column(db.String(255))

    def __repr__(self):
        return f"<Papel id={self.id} nome={self.nome!r}>"
