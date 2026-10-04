from app.infrastructure.database import db


class Unidade(db.Model):
    __tablename__ = "unidades"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    cnpj = db.Column(db.String(18), unique=True, nullable=False)
    endereco = db.Column(db.String(255))
    cidade = db.Column(db.String(120))
    uf = db.Column(db.String(2))
    telefone = db.Column(db.String(20))
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<Unidade id={self.id} nome={self.nome!r}>"
