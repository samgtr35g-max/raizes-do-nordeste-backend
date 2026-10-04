import os

from flask import Flask

from config import Config, INSTANCE_DIR
from app.api.docs.openapi import configurar_documentacao
from app.api.errors.handlers import registrar_handlers_erro, registrar_handlers_jwt
from app.api.routes import registrar_rotas
from app.infrastructure.auth import jwt
from app.infrastructure.database import db, migrate


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(INSTANCE_DIR, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    registrar_handlers_erro(app)
    registrar_handlers_jwt(jwt)

    from app.infrastructure.database import models  # noqa: F401

    registrar_rotas(app)
    configurar_documentacao(app)

    return app
