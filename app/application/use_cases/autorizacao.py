from sqlalchemy import select

from app.infrastructure.database import db
from app.infrastructure.database.models import PapelPermissao, Permissao, UsuarioPapel


def obter_codigos_permissao(usuario_id: int) -> set:
    stmt = (
        select(Permissao.codigo)
        .join(PapelPermissao, PapelPermissao.permissaoId == Permissao.id)
        .join(UsuarioPapel, UsuarioPapel.papelId == PapelPermissao.papelId)
        .where(UsuarioPapel.usuarioId == usuario_id)
        .distinct()
    )
    return set(db.session.scalars(stmt).all())


def usuario_tem_permissao(usuario_id: int, codigo: str) -> bool:
    return codigo in obter_codigos_permissao(usuario_id)
