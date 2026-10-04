from app.infrastructure.database import db


class Cliente(db.Model):
    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=True)
    email = db.Column(db.String(150))
    telefone = db.Column(db.String(20))
    dataNascimento = db.Column(db.Date)
    usuarioId = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        unique=True,
        nullable=True,
    )
    aceitaComunicacoes = db.Column(db.Boolean, nullable=False, default=False)
    consentimentoEm = db.Column(db.DateTime)
    anonimizado = db.Column(db.Boolean, nullable=False, default=False)
    criadoEm = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    usuario = db.relationship(
        "Usuario",
        backref=db.backref("cliente", uselist=False),
    )
    contaFidelidade = db.relationship(
        "ContaFidelidade",
        back_populates="cliente",
        uselist=False,
    )

    def __repr__(self):
        return f"<Cliente id={self.id} nome={self.nome!r}>"
