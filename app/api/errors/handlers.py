from app.api.errors.responses import resposta_erro
from app.domain.exceptions import ErroDeDominio
from app.infrastructure.database import db


def registrar_handlers_erro(app):
    @app.errorhandler(404)
    def _nao_encontrado(_erro):
        return resposta_erro("nao_encontrado", "Recurso nao encontrado.", 404)

    @app.errorhandler(405)
    def _metodo_nao_permitido(_erro):
        return resposta_erro("metodo_nao_permitido", "Metodo nao permitido.", 405)

    @app.errorhandler(ErroDeDominio)
    def _erro_de_dominio(erro):
        db.session.rollback()
        return resposta_erro(erro.codigo, erro.mensagem, erro.status)


def registrar_handlers_jwt(jwt):
    @jwt.unauthorized_loader
    def _token_ausente(_motivo):
        return resposta_erro("token_ausente", "Token de acesso ausente.", 401)

    @jwt.invalid_token_loader
    def _token_invalido(_motivo):
        return resposta_erro("token_invalido", "Token invalido.", 401)

    @jwt.expired_token_loader
    def _token_expirado(_header, _payload):
        return resposta_erro("token_expirado", "Token expirado.", 401)
