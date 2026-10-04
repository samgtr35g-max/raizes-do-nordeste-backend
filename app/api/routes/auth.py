from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from app.api.errors.responses import resposta_erro
from app.api.request_utils import obter_ip
from app.application.use_cases.autenticar_usuario import autenticar_usuario
from app.domain.exceptions import CredenciaisInvalidasError, UsuarioInativoError
from app.infrastructure.audit.auditoria import registrar_auditoria
from app.infrastructure.database import db
from app.infrastructure.database.models import Usuario

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.post("/login")
def login():
    dados = request.get_json(silent=True) or {}
    email = dados.get("email")
    senha = dados.get("senha")

    if not email or not senha:
        return resposta_erro("dados_invalidos", "Informe email e senha.", 400)

    try:
        usuario = autenticar_usuario(email, senha)
    except CredenciaisInvalidasError:
        registrar_auditoria(
            None,
            "Usuario",
            None,
            "LOGIN_NEGADO",
            dados_novos={"resultado": "credenciais_invalidas"},
            ip=obter_ip(request),
        )
        db.session.commit()
        return resposta_erro("credenciais_invalidas", "Email ou senha invalidos.", 401)
    except UsuarioInativoError:
        registrar_auditoria(
            None,
            "Usuario",
            None,
            "LOGIN_NEGADO",
            dados_novos={"resultado": "usuario_inativo"},
            ip=obter_ip(request),
        )
        db.session.commit()
        return resposta_erro("usuario_inativo", "Usuario inativo.", 403)

    registrar_auditoria(
        usuario.id,
        "Usuario",
        usuario.id,
        "LOGIN",
        dados_novos={"resultado": "sucesso"},
        ip=obter_ip(request),
    )
    db.session.commit()

    token = create_access_token(identity=str(usuario.id))
    expira = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES")
    return jsonify(
        {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": int(expira.total_seconds()) if expira else None,
        }
    ), 200


@auth_bp.get("/me")
@jwt_required()
def me():
    identidade = get_jwt_identity()
    usuario = db.session.get(Usuario, int(identidade))

    if usuario is None:
        return resposta_erro("nao_autenticado", "Usuario nao encontrado.", 401)

    return jsonify(
        {
            "id": usuario.id,
            "nome": usuario.nome,
            "email": usuario.email,
            "ativo": usuario.ativo,
            "unidadeId": usuario.unidadeId,
            "criadoEm": usuario.criadoEm.isoformat() if usuario.criadoEm else None,
        }
    ), 200
