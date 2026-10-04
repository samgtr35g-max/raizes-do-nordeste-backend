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
from app.application.use_cases.promocoes import calcular_desconto
from app.infrastructure.auth.passwords import gerar_hash_senha
from app.infrastructure.database import db
from app.infrastructure.database.models import (
    Estoque,
    Papel,
    Produto,
    Promocao,
    Unidade,
    Usuario,
    UsuarioPapel,
)
from app.infrastructure.database.seeds.seed import run_seed


class PromocoesTestCase(unittest.TestCase):
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
            cls.produto2_id = Produto.query.filter_by(nome="Baiao de Dois").first().id

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

    def _promo(self, tipo="PERCENTUAL", valor="10.00", produto_id=None,
               ativa=True, inicio=None, fim=None):
        with self.app.app_context():
            promocao = Promocao(
                nome="Promo Teste",
                tipoDesconto=tipo,
                valor=Decimal(valor),
                produtoId=produto_id,
                ativa=ativa,
                dataInicio=inicio or (date.today() - timedelta(days=1)),
                dataFim=fim or (date.today() + timedelta(days=1)),
            )
            db.session.add(promocao)
            db.session.commit()

    def _desconto(self, itens):
        with self.app.app_context():
            return calcular_desconto(itens)

    def test_12_percentual(self):
        self._promo(tipo="PERCENTUAL", valor="10.00", produto_id=self.produto1_id)
        desconto = self._desconto([(self.produto1_id, Decimal("100.00"))])
        self.assertEqual(desconto, Decimal("10.00"))

    def test_13_valor_fixo(self):
        self._promo(tipo="VALOR_FIXO", valor="20.00", produto_id=self.produto1_id)
        desconto = self._desconto([(self.produto1_id, Decimal("100.00"))])
        self.assertEqual(desconto, Decimal("20.00"))

    def test_14_inativa(self):
        self._promo(valor="10.00", produto_id=self.produto1_id, ativa=False)
        desconto = self._desconto([(self.produto1_id, Decimal("100.00"))])
        self.assertEqual(desconto, Decimal("0.00"))

    def test_15_fora_da_validade(self):
        self._promo(
            valor="10.00",
            produto_id=self.produto1_id,
            inicio=date.today() - timedelta(days=10),
            fim=date.today() - timedelta(days=1),
        )
        desconto = self._desconto([(self.produto1_id, Decimal("100.00"))])
        self.assertEqual(desconto, Decimal("0.00"))

    def test_16_especifica_de_produto(self):
        self._promo(valor="10.00", produto_id=self.produto1_id)
        self.assertGreater(
            self._desconto([(self.produto1_id, Decimal("100.00"))]),
            Decimal("0.00"),
        )
        self.assertEqual(
            self._desconto([(self.produto2_id, Decimal("100.00"))]),
            Decimal("0.00"),
        )

    def test_17_geral_da_rede(self):
        self._promo(valor="10.00", produto_id=None)
        self.assertGreater(
            self._desconto([(self.produto2_id, Decimal("100.00"))]),
            Decimal("0.00"),
        )

    def test_18_escolhe_maior_beneficio(self):
        self._promo(tipo="PERCENTUAL", valor="10.00", produto_id=None)
        self._promo(tipo="VALOR_FIXO", valor="30.00", produto_id=self.produto1_id)
        desconto = self._desconto([(self.produto1_id, Decimal("100.00"))])
        self.assertEqual(desconto, Decimal("30.00"))

    def test_19_desconto_nao_negativo(self):
        self._promo(tipo="VALOR_FIXO", valor="200.00", produto_id=self.produto1_id)
        desconto = self._desconto([(self.produto1_id, Decimal("100.00"))])
        self.assertEqual(desconto, Decimal("100.00"))

    def test_20_servidor_ignora_valores_do_cliente(self):
        self._promo(tipo="PERCENTUAL", valor="10.00", produto_id=self.produto1_id)
        token = self._gerente_token()
        resp = self.client.post(
            "/pedidos",
            json={
                "unidadeId": self.unidade_a_id,
                "canalPedido": "BALCAO",
                "valorDesconto": "999.99",
                "valorTotal": "0.01",
                "itens": [
                    {
                        "produtoId": self.produto1_id,
                        "quantidade": 1,
                        "valorUnitario": "0.01",
                    }
                ],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        corpo = resp.get_json()
        self.assertEqual(corpo["valorProdutos"], "12.00")
        self.assertEqual(corpo["valorDesconto"], "1.20")
        self.assertEqual(corpo["valorTotal"], "10.80")


if __name__ == "__main__":
    unittest.main()
