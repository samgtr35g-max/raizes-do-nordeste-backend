from flask import jsonify


def resposta_erro(codigo: str, mensagem: str, status: int):
    return jsonify({"erro": {"codigo": codigo, "mensagem": mensagem}}), status
