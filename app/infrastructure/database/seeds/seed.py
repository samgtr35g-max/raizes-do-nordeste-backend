"""Seed inicial de desenvolvimento.

Cria dados ficticios e minimos apenas para desenvolvimento/testes.
Nao implementa regras de negocio nem endpoints.

Credenciais de desenvolvimento (apenas para testar o login localmente):
    Administrador da rede : admin@raizes.dev      / Admin@123
    Atendente (unidade)   : atendente@raizes.dev  / Atendente@123

    Essas credenciais sao exclusivas de ambiente de desenvolvimento e
    NAO devem ser usadas em producao. As senhas sao armazenadas como
    hash real, gerado pela rotina oficial em
    `app.infrastructure.auth.passwords`.
"""
from decimal import Decimal

from app.infrastructure.auth.passwords import gerar_hash_senha
from app.infrastructure.database import db
from app.infrastructure.database.models import (
    Categoria,
    Cliente,
    ContaFidelidade,
    Estoque,
    Papel,
    PapelPermissao,
    Permissao,
    Produto,
    Unidade,
    Usuario,
    UsuarioPapel,
)

ADMIN_EMAIL = "admin@raizes.dev"
ADMIN_SENHA = "Admin@123"
ATENDENTE_EMAIL = "atendente@raizes.dev"
ATENDENTE_SENHA = "Atendente@123"

SENHA_HASH_PROVISORIO = "DEV-SEED-PLACEHOLDER-NAO-E-HASH-VALIDO"


def _get_or_create(model, defaults=None, **filters):
    instance = model.query.filter_by(**filters).first()
    if instance is not None:
        return instance, False
    params = dict(filters)
    if defaults:
        params.update(defaults)
    instance = model(**params)
    db.session.add(instance)
    db.session.flush()
    return instance, True


def _garantir_senha(usuario, senha):
    if usuario.senhaHash == SENHA_HASH_PROVISORIO or not usuario.senhaHash:
        usuario.senhaHash = gerar_hash_senha(senha)


def run_seed():
    unidade, _ = _get_or_create(
        Unidade,
        cnpj="00.000.000/0001-00",
        defaults={
            "nome": "Raizes do Nordeste - Matriz (DEV)",
            "endereco": "Rua de Teste, 100",
            "cidade": "Recife",
            "uf": "PE",
            "telefone": "(81) 0000-0000",
            "ativo": True,
        },
    )

    categorias = {}
    for nome in ("Bebidas", "Pratos", "Sobremesas"):
        categorias[nome], _ = _get_or_create(
            Categoria, nome=nome, defaults={"ativo": True}
        )

    produtos_def = (
        ("Suco de Caja", "Bebidas", "12.00", 50, 10),
        ("Baiao de Dois", "Pratos", "32.90", 30, 5),
        ("Cartola", "Sobremesas", "18.50", 20, 5),
    )
    for nome, categoria, preco, quantidade, quantidade_minima in produtos_def:
        produto, _ = _get_or_create(
            Produto,
            nome=nome,
            defaults={
                "descricao": f"Item de teste (DEV): {nome}",
                "precoBase": Decimal(preco),
                "categoriaId": categorias[categoria].id,
                "ativo": True,
            },
        )
        _get_or_create(
            Estoque,
            unidadeId=unidade.id,
            produtoId=produto.id,
            defaults={
                "quantidadeAtual": quantidade,
                "quantidadeMinima": quantidade_minima,
            },
        )

    papeis = {}
    for nome, descricao in (
        ("ADMIN", "Administrador da rede"),
        ("GERENTE", "Gerente de unidade"),
        ("ATENDENTE", "Atendente de loja"),
    ):
        papeis[nome], _ = _get_or_create(
            Papel, nome=nome, defaults={"descricao": descricao}
        )

    permissoes = {}
    for codigo, descricao in (
        ("ESTOQUE_AJUSTAR", "Ajustar estoque"),
        ("PEDIDO_CANCELAR", "Cancelar pedido"),
        ("PRODUTO_GERENCIAR", "Gerenciar produtos"),
        ("USUARIO_GERENCIAR", "Gerenciar usuarios"),
    ):
        permissoes[codigo], _ = _get_or_create(
            Permissao, codigo=codigo, defaults={"descricao": descricao}
        )

    papeis_permissoes = {
        "ADMIN": (
            "ESTOQUE_AJUSTAR",
            "PEDIDO_CANCELAR",
            "PRODUTO_GERENCIAR",
            "USUARIO_GERENCIAR",
        ),
        "GERENTE": ("ESTOQUE_AJUSTAR", "PEDIDO_CANCELAR", "PRODUTO_GERENCIAR"),
        "ATENDENTE": ("PEDIDO_CANCELAR",),
    }
    for papel_nome, codigos in papeis_permissoes.items():
        for codigo in codigos:
            _get_or_create(
                PapelPermissao,
                papelId=papeis[papel_nome].id,
                permissaoId=permissoes[codigo].id,
            )

    admin, _ = _get_or_create(
        Usuario,
        email=ADMIN_EMAIL,
        defaults={
            "nome": "Administrador DEV",
            "senhaHash": gerar_hash_senha(ADMIN_SENHA),
            "ativo": True,
            "unidadeId": None,
        },
    )
    _garantir_senha(admin, ADMIN_SENHA)

    atendente, _ = _get_or_create(
        Usuario,
        email=ATENDENTE_EMAIL,
        defaults={
            "nome": "Atendente DEV",
            "senhaHash": gerar_hash_senha(ATENDENTE_SENHA),
            "ativo": True,
            "unidadeId": unidade.id,
        },
    )
    _garantir_senha(atendente, ATENDENTE_SENHA)

    _get_or_create(UsuarioPapel, usuarioId=admin.id, papelId=papeis["ADMIN"].id)
    _get_or_create(UsuarioPapel, usuarioId=atendente.id, papelId=papeis["ATENDENTE"].id)

    cliente, _ = _get_or_create(
        Cliente,
        email="cliente.teste@raizes.dev",
        defaults={
            "nome": "Cliente Teste DEV",
            "cpf": None,
            "telefone": "(81) 90000-0000",
            "aceitaComunicacoes": False,
            "anonimizado": False,
        },
    )
    _get_or_create(
        ContaFidelidade,
        clienteId=cliente.id,
        defaults={"saldoPontos": 0},
    )

    db.session.commit()


if __name__ == "__main__":
    from app import create_app

    app = create_app()
    with app.app_context():
        run_seed()
        print("Seed executado com sucesso.")
