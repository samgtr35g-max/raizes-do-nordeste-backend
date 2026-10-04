from app.infrastructure.database import db


class Produto(db.Model):
    __tablename__ = "produtos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    descricao = db.Column(db.String(255))
    precoBase = db.Column(db.Numeric(10, 2), nullable=False)
    categoriaId = db.Column(
        db.Integer,
        db.ForeignKey("categorias.id"),
        nullable=False,
    )
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    categoria = db.relationship("Categoria", backref="produtos")
    promocoes = db.relationship("Promocao", back_populates="produto")

    def __repr__(self):
        return f"<Produto id={self.id} nome={self.nome!r}>"
