import os
import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal

_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = "sqlite:///" + _db_path.replace("\\", "/")
os.environ["JWT_SECRET_KEY"] = "chave-jwt-de-teste-com-32-bytes-ou-mais-123456"

from sqlalchemy import select

from app import create_app
from app.application.use_cases import pedidos as pedidos_uc
from app.infrastructure.auth.passwords import gerar_hash_senha
from app.infrastructure.database import db
from app.infrastructure.database.models import (
    Estoque,
    Papel,
    Pedido,
    Produto,
    Promocao,
    Unidade,
    Usuario,
    UsuarioPapel,
)
from app.infrastructure.database.seeds.seed import run_seed


class IntegracaoTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            db.create_all()
            run_seed()
            unidade_a = Unidade.query.filter_by(cnpj="00.000.000/0001-00").first()
            cls.unidade_a_id = unidade_a.id
            cls.produto1_id = Produto.query.filter_by(nome="Suco de Caja").first().id

            for estoque in Estoque.query.filter_by(unidadeId=unidade_a.id).all():
                estoque.quantidadeAtual = 1000

            papel_gerente = Papel.query.filter_by(nome="GERENTE").first()
            gerente = Usuario(
                nome="Gerente A",
                email="gerente.a@test.dev",
                senhaHash=gerar_hash_senha("Gerente@123"),
                ativo=True,
                unidadeId=unidade_a.id,
            )
            db.session.add(gerente)
            db.session.flush()
            db.session.add(
                UsuarioPapel(usuarioId=gerente.id, papelId=papel_gerente.id)
            )
            db.session.commit()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        if os.path.exists(_db_path):
            os.remove(_db_path)

    def setUp(self):
        with self.app.app_context():
            for promocao in db.session.scalars(select(Promocao)).all():
                db.session.delete(promocao)
            db.session.commit()

    def _gerente_token(self):
        resp = self.client.post(
            "/auth/login",
            json={"email": "gerente.a@test.dev", "senha": "Gerente@123"},
        )
        return resp.get_json()["access_token"]

    def _headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _promo_percentual(self):
        with self.app.app_context():
            db.session.add(
                Promocao(
                    nome="10% Suco",
                    tipoDesconto="PERCENTUAL",
                    valor=Decimal("10.00"),
                    produtoId=self.produto1_id,
                    ativa=True,
                    dataInicio=date.today() - timedelta(days=1),
                    dataFim=date.today() + timedelta(days=1),
                )
            )
            db.session.commit()

    def _criar_pedido(self, token, quantidade=2):
        return self.client.post(
            "/pedidos",
            json={
                "unidadeId": self.unidade_a_id,
                "canalPedido": "BALCAO",
                "itens": [
                    {"produtoId": self.produto1_id, "quantidade": quantidade}
                ],
            },
            headers=self._headers(token),
        )

    def _qtd(self):
        with self.app.app_context():
            estoque = db.session.scalar(
                select(Estoque).filter_by(
                    unidadeId=self.unidade_a_id, produtoId=self.produto1_id
                )
            )
            return estoque.quantidadeAtual

    def test_21_pedido_calcula_desconto(self):
        self._promo_percentual()
        corpo = self._criar_pedido(self._gerente_token()).get_json()
        self.assertEqual(corpo["valorProdutos"], "24.00")
        self.assertEqual(corpo["valorDesconto"], "2.40")

    def test_22_pedido_calcula_valor_total(self):
        self._promo_percentual()
        corpo = self._criar_pedido(self._gerente_token()).get_json()
        self.assertEqual(corpo["valorTotal"], "21.60")

    def test_23_estoque_continua_funcionando(self):
        token = self._gerente_token()
        antes = self._qtd()
        resp = self._criar_pedido(token, quantidade=2)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(self._qtd(), antes - 2)

    def test_24_pagamento_continua_funcionando(self):
        token = self._gerente_token()
        pedido_id = self._criar_pedido(token).get_json()["id"]
        resp = self.client.post(
            "/pagamentos",
            json={"pedidoId": pedido_id, "metodo": "PIX", "simularResultado": "APROVADO"},
            headers=self._headers(token),
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["status"], "APROVADO")

    def test_25_cancelamento_continua_funcionando(self):
        token = self._gerente_token()
        antes = self._qtd()
        pedido_id = self._criar_pedido(token, quantidade=3).get_json()["id"]
        resp = self.client.post(
            f"/pedidos/{pedido_id}/cancelamento",
            json={},
            headers=self._headers(token),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "CANCELADO")
        self.assertEqual(self._qtd(), antes)

    def test_26_rollback_em_caso_de_erro(self):
        with self.app.app_context():
            antes_pedidos = len(db.session.scalars(select(Pedido)).all())
            antes_qtd = self._qtd()

            original = pedidos_uc._registrar_historico

            def falha(*_args, **_kwargs):
                raise RuntimeError("falha simulada")

            pedidos_uc._registrar_historico = falha
            try:
                with self.assertRaises(RuntimeError):
                    pedidos_uc.criar_pedido(
                        self.unidade_a_id,
                        "BALCAO",
                        [{"produtoId": self.produto1_id, "quantidade": 1}],
                        usuario_id=None,
                    )
            finally:
                pedidos_uc._registrar_historico = original
                db.session.rollback()

            depois_pedidos = len(db.session.scalars(select(Pedido)).all())
            self.assertEqual(depois_pedidos, antes_pedidos)
            self.assertEqual(self._qtd(), antes_qtd)


if __name__ == "__main__":
    unittest.main()
