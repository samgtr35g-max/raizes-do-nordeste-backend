"""Servico de auditoria.

Registra acoes relevantes em `LogAuditoria`, dentro da transacao atual
(sem commit proprio), permitindo rollback consistente. Mascara campos
sensiveis antes de persistir.
"""
from app.infrastructure.database import db
from app.infrastructure.database.models import LogAuditoria

CHAVES_SENSIVEIS = {
    "senha",
    "senhahash",
    "senha_hash",
    "password",
    "passwd",
    "token",
    "access_token",
    "authorization",
    "jwt",
    "jwt_secret_key",
    "secret",
    "cvv",
    "cvc",
    "cartao",
    "card",
    "numero_cartao",
    "pan",
    "credenciais",
    "credentials",
}

MASCARA = "***"


def _sanitizar(dados):
    if isinstance(dados, dict):
        return {
            chave: (MASCARA if str(chave).lower() in CHAVES_SENSIVEIS else _sanitizar(valor))
            for chave, valor in dados.items()
        }
    if isinstance(dados, list):
        return [_sanitizar(item) for item in dados]
    return dados


def registrar_auditoria(
    usuario_id,
    entidade,
    entidade_id,
    acao,
    dados_anteriores=None,
    dados_novos=None,
    ip=None,
):
    registro = LogAuditoria(
        usuarioId=usuario_id,
        entidade=entidade,
        entidadeId=entidade_id,
        acao=acao,
        dadosAnteriores=_sanitizar(dados_anteriores),
        dadosNovos=_sanitizar(dados_novos),
        ip=ip,
    )
    db.session.add(registro)
    return registro
