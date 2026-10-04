from functools import wraps

from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.api.errors.responses import resposta_erro
from app.application.use_cases.autorizacao import usuario_tem_permissao
from app.infrastructure.database import db
from app.infrastructure.database.models import Usuario


def exigir_permissao(codigo: str):
    def decorator(funcao):
        @wraps(funcao)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            identidade = get_jwt_identity()
            usuario = db.session.get(Usuario, int(identidade))
            if usuario is None:
                return resposta_erro("nao_autenticado", "Usuario nao encontrado.", 401)
            if not usuario.ativo:
                return resposta_erro("usuario_inativo", "Usuario inativo.", 403)
            if not usuario_tem_permissao(usuario.id, codigo):
                return resposta_erro("acesso_negado", "Permissao insuficiente.", 403)
            return funcao(*args, **kwargs)

        return wrapper

    return decorator
