from werkzeug.security import check_password_hash, generate_password_hash


def gerar_hash_senha(senha: str) -> str:
    return generate_password_hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    if not senha_hash:
        return False
    return check_password_hash(senha_hash, senha)
