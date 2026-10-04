"""Rotas de desenvolvimento/teste para demonstrar a autorizacao (RBAC).

Nao sao endpoints de negocio: existem apenas para validar o mecanismo
`exigir_permissao`. A permissao exigida e fixada no servidor por rota,
nunca vinda do cliente.
"""
from flask import Blueprint, jsonify

from app.api.routes.guards import exigir_permissao

dev_bp = Blueprint("dev_rbac", __name__, url_prefix="/dev/rbac")


@dev_bp.get("/estoque-ajustar")
@exigir_permissao("ESTOQUE_AJUSTAR")
def dev_estoque_ajustar():
    return jsonify({"ok": True, "permissao": "ESTOQUE_AJUSTAR"}), 200


@dev_bp.get("/pedido-cancelar")
@exigir_permissao("PEDIDO_CANCELAR")
def dev_pedido_cancelar():
    return jsonify({"ok": True, "permissao": "PEDIDO_CANCELAR"}), 200


@dev_bp.get("/produto-gerenciar")
@exigir_permissao("PRODUTO_GERENCIAR")
def dev_produto_gerenciar():
    return jsonify({"ok": True, "permissao": "PRODUTO_GERENCIAR"}), 200


@dev_bp.get("/usuario-gerenciar")
@exigir_permissao("USUARIO_GERENCIAR")
def dev_usuario_gerenciar():
    return jsonify({"ok": True, "permissao": "USUARIO_GERENCIAR"}), 200
