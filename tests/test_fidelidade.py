import itertools
import os
import tempfile
import unittest
from decimal import Decimal

_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = "sqlite:///" + _db_path.replace("\\", "/")
os.environ["JWT_SECRET_KEY"] = "chave-jwt-de-teste-com-32-bytes-ou-mais-123456"

from sqlalchemy import select

from app import create_app
from app.application.use_cases import fidelidade as fid
from app.application.use_cases.pedidos import cancelar_pedido
from app.infrastructure.auth.passwords import gerar_hash_senha
from app.infrastructure.database import db
from app.infrastructure.database.models import (
    Cliente,
    ContaFidelidade,
    MovimentacaoPontos,
    Papel,
    Pedido,
    Unidade,
    Usuario,
    UsuarioPapel,
)
from app.infrastructure.database.seeds.seed import run_seed


class FidelidadeTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        cls._contador = itertools.count(1)
        with cls.app.app_context():
            db.create_all()
            run_seed()
            unidade_a = Unidade.query.filter_by(cnpj="00.000.000/0001-00").first()
            cls.unidade_a_id = unidade_a.id
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

    def _admin_token(self):
        resp = self.client.post(
            "/auth/login",
            json={"email": "admin@raizes.dev", "senha": "Admin@123"},
        )
        return resp.get_json()["access_token"]

    def _headers(self, token):
        return {"Authorization": f"Bearer {token}"} if token else {}

    def _novo_cliente(self, com_conta=True):
        with self.app.app_context():
            n = next(self._contador)
            cliente = Cliente(nome=f"Cliente {n}", email=f"cli{n}@test.dev")
            db.session.add(cliente)
            db.session.flush()
            if com_conta:
                db.session.add(
                    ContaFidelidade(clienteId=cliente.id, saldoPontos=0)
                )
            db.session.commit()
            return cliente.id

    def _novo_pedido(self, cliente_id, valor="35.90"):
        with self.app.app_context():
            pedido = Pedido(
                unidadeId=self.unidade_a_id,
                clienteId=cliente_id,
                canalPedido="BALCAO",
                status="RECEBIDO",
                valorProdutos=Decimal(valor),
                valorDesconto=Decimal("0.00"),
                valorTotal=Decimal(valor),
            )
            db.session.add(pedido)
            db.session.commit()
            return pedido.id

    def _saldo(self, cliente_id):
        with self.app.app_context():
            conta = db.session.scalar(
                select(ContaFidelidade).filter_by(clienteId=cliente_id)
            )
            return conta.saldoPontos if conta else None

    def _movs(self, cliente_id):
        with self.app.app_context():
            conta = db.session.scalar(
                select(ContaFidelidade).filter_by(clienteId=cliente_id)
            )
            return db.session.scalars(
                select(MovimentacaoPontos)
                .where(MovimentacaoPontos.contaFidelidadeId == conta.id)
                .order_by(MovimentacaoPontos.id)
            ).all()

    def _acumular(self, pedido_id):
        with self.app.app_context():
            pedido = db.session.get(Pedido, pedido_id)
            fid.acumular_pontos_por_pedido(pedido)
            db.session.commit()

    def test_1_conta_criada_ao_consultar(self):
        cliente_id = self._novo_cliente(com_conta=False)
        token = self._admin_token()
        resp = self.client.get(
            f"/clientes/{cliente_id}/fidelidade", headers=self._headers(token)
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["saldoPontos"], 0)
        with self.app.app_context():
            conta = db.session.scalar(
                select(ContaFidelidade).filter_by(clienteId=cliente_id)
            )
            self.assertIsNotNone(conta)

    def test_2_saldo_inicial(self):
        cliente_id = self._novo_cliente()
        token = self._admin_token()
        resp = self.client.get(
            f"/clientes/{cliente_id}/fidelidade", headers=self._headers(token)
        )
        self.assertEqual(resp.get_json()["saldoPontos"], 0)

    def test_3_acumulo_de_pontos(self):
        cliente_id = self._novo_cliente()
        pedido_id = self._novo_pedido(cliente_id, "35.90")
        self._acumular(pedido_id)
        self.assertEqual(self._saldo(cliente_id), 35)

    def test_4_nao_duplicar_acumulo(self):
        cliente_id = self._novo_cliente()
        pedido_id = self._novo_pedido(cliente_id, "35.90")
        self._acumular(pedido_id)
        self._acumular(pedido_id)
        self.assertEqual(self._saldo(cliente_id), 35)
        tipos = [m.tipo for m in self._movs(cliente_id)]
        self.assertEqual(tipos.count("ACUMULO"), 1)

    def test_5_resgate_valido(self):
        cliente_id = self._novo_cliente()
        pedido_id = self._novo_pedido(cliente_id, "100.00")
        self._acumular(pedido_id)
        token = self._admin_token()
        resp = self.client.post(
            f"/clientes/{cliente_id}/fidelidade/resgate",
            json={"pontos": 20},
            headers=self._headers(token),
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["saldoPontos"], 80)

    def test_6_resgate_maior_que_saldo(self):
        cliente_id = self._novo_cliente()
        pedido_id = self._novo_pedido(cliente_id, "10.00")
        self._acumular(pedido_id)
        token = self._admin_token()
        resp = self.client.post(
            f"/clientes/{cliente_id}/fidelidade/resgate",
            json={"pontos": 20},
            headers=self._headers(token),
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "saldo_insuficiente")

    def test_7_resgate_quantidade_invalida(self):
        cliente_id = self._novo_cliente()
        token = self._admin_token()
        for pontos in (0, -1, 1.5, "x"):
            resp = self.client.post(
                f"/clientes/{cliente_id}/fidelidade/resgate",
                json={"pontos": pontos},
                headers=self._headers(token),
            )
            self.assertEqual(resp.status_code, 422)

    def test_8_saldo_nunca_negativo(self):
        cliente_id = self._novo_cliente()
        pedido_id = self._novo_pedido(cliente_id, "5.00")
        self._acumular(pedido_id)
        token = self._admin_token()
        self.client.post(
            f"/clientes/{cliente_id}/fidelidade/resgate",
            json={"pontos": 5},
            headers=self._headers(token),
        )
        resp = self.client.post(
            f"/clientes/{cliente_id}/fidelidade/resgate",
            json={"pontos": 1},
            headers=self._headers(token),
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(self._saldo(cliente_id), 0)

    def test_9_estorno_no_cancelamento(self):
        cliente_id = self._novo_cliente()
        pedido_id = self._novo_pedido(cliente_id, "50.00")
        self._acumular(pedido_id)
        self.assertEqual(self._saldo(cliente_id), 50)
        with self.app.app_context():
            cancelar_pedido(pedido_id, usuario_id=None)
        self.assertEqual(self._saldo(cliente_id), 0)
        tipos = [m.tipo for m in self._movs(cliente_id)]
        self.assertIn("ESTORNO", tipos)

    def test_10_nao_duplicar_estorno(self):
        cliente_id = self._novo_cliente()
        pedido_id = self._novo_pedido(cliente_id, "50.00")
        self._acumular(pedido_id)
        with self.app.app_context():
            cancelar_pedido(pedido_id, usuario_id=None)
            pedido = db.session.get(Pedido, pedido_id)
            fid.estornar_pontos_por_pedido(pedido)
            db.session.commit()
        tipos = [m.tipo for m in self._movs(cliente_id)]
        self.assertEqual(tipos.count("ESTORNO"), 1)

    def test_11_historico_movimentacoes(self):
        cliente_id = self._novo_cliente()
        pedido_id = self._novo_pedido(cliente_id, "40.00")
        self._acumular(pedido_id)
        token = self._admin_token()
        self.client.post(
            f"/clientes/{cliente_id}/fidelidade/resgate",
            json={"pontos": 10},
            headers=self._headers(token),
        )
        resp = self.client.get(
            f"/clientes/{cliente_id}/fidelidade", headers=self._headers(token)
        )
        movs = resp.get_json()["movimentacoes"]
        tipos = [m["tipo"] for m in movs]
        self.assertEqual(tipos, ["ACUMULO", "RESGATE"])
        self.assertEqual(resp.get_json()["saldoPontos"], 30)


if __name__ == "__main__":
    unittest.main()
