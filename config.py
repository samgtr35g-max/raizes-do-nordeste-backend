import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
DEFAULT_DATABASE_PATH = INSTANCE_DIR / "raizes.db"

# Valores de exemplo/placeholder que NAO devem ser aceitos como chave JWT real.
_JWT_SECRET_KEY_INVALIDAS = {
    "",
    "dev-secret",
    "troque-por-uma-chave-secreta",
    "troque-por-uma-chave-jwt-secreta",
}

_JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not _JWT_SECRET_KEY or _JWT_SECRET_KEY in _JWT_SECRET_KEY_INVALIDAS:
    raise RuntimeError(
        "A variavel de ambiente JWT_SECRET_KEY e obrigatoria e nao foi "
        "configurada corretamente. Defina uma chave secreta real (nao use os "
        "valores de exemplo) no arquivo .env antes de iniciar a aplicacao."
    )


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = _JWT_SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_HOURS", "8"))
    )
