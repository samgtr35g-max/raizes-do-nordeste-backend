import json
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
from app.infrastructure.auth.passwords import gerar_hash_senha
from app.infrastructure.database import db
from app.infrastructure.database.models import (
    Estoque,
    Pagamento,
    Papel,
    Produto,
    Unidade,
    Usuario,
    UsuarioPapel,
)
from app.infrastructure.database.seeds.seed import run_seed


class PagamentosTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            db.create_all()
            run_seed()

            unidade_a = Unidade.query.filter_by(cnpj="00.000.000/0001-00").first()
            unidade_b = Unidade(
                nome="Unidade B (TESTE)", cnpj="11.111.111/0001-11", ativo=True
            )
            db.session.add(unidade_b)
            db.session.flush()
            cls.unidade_a_id = unidade_a.id
            cls.unidade_b_id = unidade_b.id
            cls.produto1_id = Produto.query.filter_by(nome="Suco de Caja").first().id

            for estoque in Estoque.query.filter_by(unidadeId=unidade_a.id).all():
                estoque.quantidadeAtual = 1000
            db.session.add(
                Estoque(
                    unidadeId=unidade_b.id,
                    produtoId=cls.produto1_id,
                    quantidadeAtual=1000,
                    quantidadeMinima=0,
                )
            )

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

    def _token(self, email, senha):
        resp = self.client.post("/auth/login", json={"email": email, "senha": senha})
        return resp.get_json()["access_token"]

    def _gerente_token(self):
        return self._token("gerente.a@test.dev", "Gerente@123")

    def _admin_token(self):
        return self._token("admin@raizes.dev", "Admin@123")

    def _headers(self, token):
        return {"Authorization": f"Bearer {token}"} if token else {}

    def _criar_pedido(self, token, unidade_id=None, qty=1):
        resp = self.client.post(
            "/pedidos",
            json={
                "unidadeId": unidade_id or self.unidade_a_id,
                "canalPedido": "BALCAO",
                "itens": [{"produtoId": self.produto1_id, "quantidade": qty}],
            },
            headers=self._headers(token),
        )
        assert resp.status_code == 201, resp.get_json()
        return resp.get_json()

    def _pagar(self, token, pedido_id, metodo, simular=None, extra=None):
        payload = {"pedidoId": pedido_id, "metodo": metodo}
        if simular is not None:
            payload["simularResultado"] = simular
        if extra:
            payload.update(extra)
        return self.client.post(
            "/pagamentos", json=payload, headers=self._headers(token)
        )

    def test_1_pix_aprovado(self):
        pedido = self._criar_pedido(self._gerente_token())
        resp = self._pagar(
            self._gerente_token(), pedido["id"], "PIX", simular="APROVADO"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["status"], "APROVADO")

    def test_2_pix_recusado(self):
        pedido = self._criar_pedido(self._gerente_token())
        resp = self._pagar(
            self._gerente_token(), pedido["id"], "PIX", simular="RECUSADO"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["status"], "RECUSADO")

    def test_3_cartao_aprovado(self):
        pedido = self._criar_pedido(self._gerente_token())
        resp = self._pagar(
            self._gerente_token(), pedido["id"], "CARTAO", simular="APROVADO"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["status"], "APROVADO")

    def test_4_cartao_recusado(self):
        pedido = self._criar_pedido(self._gerente_token())
        resp = self._pagar(
            self._gerente_token(), pedido["id"], "CARTAO", simular="RECUSADO"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["status"], "RECUSADO")

    def test_5_dinheiro_aprovado(self):
        pedido = self._criar_pedido(self._gerente_token())
        resp = self._pagar(self._gerente_token(), pedido["id"], "DINHEIRO")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["status"], "APROVADO")

    def test_6_pedido_inexistente(self):
        resp = self._pagar(self._gerente_token(), 999999, "PIX")
        self.assertEqual(resp.status_code, 404)

    def test_7_pedido_cancelado(self):
        token = self._gerente_token()
        pedido_id = self._criar_pedido(token)["id"]
        self.client.post(
            f"/pedidos/{pedido_id}/cancelamento",
            json={},
            headers=self._headers(token),
        )
        resp = self._pagar(token, pedido_id, "PIX")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "pagamento_nao_permitido")

    def test_8_metodo_invalido(self):
        pedido = self._criar_pedido(self._gerente_token())
        resp = self._pagar(self._gerente_token(), pedido["id"], "BOLETO")
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "dados_invalidos")

    def test_9_valor_obtido_do_pedido(self):
        token = self._gerente_token()
        pedido = self._criar_pedido(token, qty=2)
        resp = self._pagar(
            token, pedido["id"], "PIX", extra={"valor": "0.01"}
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["valor"], pedido["valorTotal"])

    def test_10_pagamento_duplicado(self):
        token = self._gerente_token()
        pedido_id = self._criar_pedido(token)["id"]
        self._pagar(token, pedido_id, "PIX", simular="APROVADO")
        resp = self._pagar(token, pedido_id, "PIX", simular="APROVADO")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "pagamento_duplicado")

    def test_11_id_transacao_armazenado(self):
        token = self._gerente_token()
        pedido_id = self._criar_pedido(token)["id"]
        corpo = self._pagar(token, pedido_id, "PIX", simular="APROVADO").get_json()
        self.assertIsNotNone(corpo["idTransacaoExterna"])
        self.assertTrue(corpo["idTransacaoExterna"].startswith("MOCK-"))

    def test_12_resposta_segura(self):
        token = self._gerente_token()
        pedido_id = self._criar_pedido(token)["id"]
        criado = self._pagar(token, pedido_id, "CARTAO", simular="APROVADO").get_json()
        payload = json.loads(criado["payloadResposta"])
        self.assertEqual(
            set(payload.keys()),
            {"status", "idTransacaoExterna", "provedor", "mensagem"},
        )
        bruto = json.dumps(payload).lower()
        for proibido in ("cvv", "senha", "numero", "bandeira", "token"):
            self.assertNotIn(proibido, bruto)

    def test_13_sem_jwt(self):
        pedido = self._criar_pedido(self._gerente_token())
        resp = self.client.post(
            "/pagamentos", json={"pedidoId": pedido["id"], "metodo": "PIX"}
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "token_ausente")

    def test_14_outra_unidade(self):
        admin = self._admin_token()
        pedido_b = self._criar_pedido(admin, unidade_id=self.unidade_b_id)
        resp = self._pagar(self._gerente_token(), pedido_b["id"], "PIX")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "acesso_negado")

    def test_15_rollback_falha(self):
        token = self._gerente_token()
        pedido_id = self._criar_pedido(token)["id"]

        with self.app.app_context():
            import app.application.use_cases.pagamentos as uc

            original = uc._confirmar

            def falha():
                raise RuntimeError("falha simulada")

            uc._confirmar = falha
            try:
                with self.assertRaises(RuntimeError):
                    uc.criar_pagamento(pedido_id, "PIX", usuario_id=None)
            finally:
                uc._confirmar = original
                db.session.rollback()

            pagamentos = db.session.scalars(
                select(Pagamento).where(Pagamento.pedidoId == pedido_id)
            ).all()
            self.assertEqual(len(pagamentos), 0)

    def test_16_consulta_pagamento(self):
        token = self._gerente_token()
        pedido_id = self._criar_pedido(token)["id"]
        pagamento_id = self._pagar(token, pedido_id, "PIX").get_json()["id"]
        resp = self.client.get(
            f"/pagamentos/{pagamento_id}", headers=self._headers(token)
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["id"], pagamento_id)

    def test_17_consulta_inexistente(self):
        resp = self.client.get(
            "/pagamentos/999999", headers=self._headers(self._gerente_token())
        )
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
