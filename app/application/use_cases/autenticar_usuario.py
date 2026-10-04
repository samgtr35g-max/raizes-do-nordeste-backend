from sqlalchemy import select

from app.domain.exceptions import CredenciaisInvalidasError, UsuarioInativoError
from app.infrastructure.auth.passwords import verificar_senha
from app.infrastructure.database import db
from app.infrastructure.database.models import Usuario


def autenticar_usuario(email: str, senha: str) -> Usuario:
    usuario = db.session.scalar(select(Usuario).filter_by(email=email))
    if usuario is None or not verificar_senha(senha, usuario.senhaHash):
        raise CredenciaisInvalidasError()
    if not usuario.ativo:
        raise UsuarioInativoError()
    return usuario
