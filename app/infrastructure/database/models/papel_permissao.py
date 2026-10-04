from app.infrastructure.database import db


class PapelPermissao(db.Model):
    __tablename__ = "papeis_permissoes"

    papelId = db.Column(
        db.Integer,
        db.ForeignKey("papeis.id"),
        primary_key=True,
    )
    permissaoId = db.Column(
        db.Integer,
        db.ForeignKey("permissoes.id"),
        primary_key=True,
    )

    def __repr__(self):
        return f"<PapelPermissao papelId={self.papelId} permissaoId={self.permissaoId}>"
