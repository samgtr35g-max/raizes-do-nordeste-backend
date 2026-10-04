import json
import os
import tempfile
import unittest

_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = "sqlite:///" + _db_path.replace("\\", "/")
os.environ["JWT_SECRET_KEY"] = "chave-jwt-de-teste-com-32-bytes-ou-mais-123456"

from sqlalchemy import select

from app import create_app
from app.application.use_cases import pedidos as pedidos_uc
from app.infrastructure.audit.auditoria import registrar_auditoria
from app.infrastructure.auth.passwords import gerar_hash_senha
from app.infrastructure.database import db
from app.infrastructure.database.models import (
    Cliente,
    ContaFidelidade,
    Estoque,
    LogAuditoria,
    Papel,
    Produto,
    Unidade,
    Usuario,
    UsuarioPapel,
)
from app.infrastructure.database.seeds.seed import run_seed


class AuditoriaLGPDTestCase(unittest.TestCase):
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
            cls.produto_id = Produto.query.filter_by(nome="Suco de Caja").first().id
            cls.cliente_id = (
                Cliente.query.filter_by(email="cliente.teste@raizes.dev").first().id
            )

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

    def _token(self, email, senha):
        resp = self.client.post("/auth/login", json={"email": email, "senha": senha})
        return resp.get_json()["access_token"]

    def _gerente_token(self):
        return self._token("gerente.a@test.dev", "Gerente@123")

    def _admin_token(self):
        return self._token("admin@raizes.dev", "Admin@123")

    def _headers(self, token):
        return {"Authorization": f"Bearer {token}"} if token else {}

    def _logs(self, acao):
        with self.app.app_context():
            return db.session.scalars(
                select(LogAuditoria)
                .where(LogAuditoria.acao == acao)
                .order_by(LogAuditoria.id)
            ).all()

    def _criar_pedido(self, token, cliente_id=None, qty=1):
        payload = {
            "unidadeId": self.unidade_a_id,
            "canalPedido": "BALCAO",
            "itens": [{"produtoId": self.produto_id, "quantidade": qty}],
        }
        if cliente_id is not None:
            payload["clienteId"] = cliente_id
        return self.client.post("/pedidos", json=payload, headers=self._headers(token))

    def _qtd(self):
        with self.app.app_context():
            return db.session.scalar(
                select(Estoque).filter_by(
                    unidadeId=self.unidade_a_id, produtoId=self.produto_id
                )
            ).quantidadeAtual

    # ---------- Auditoria de acoes ----------

    def test_1_auditoria_login(self):
        self._gerente_token()
        with self.app.app_context():
            gerente = Usuario.query.filter_by(email="gerente.a@test.dev").first()
        logs = self._logs("LOGIN")
        self.assertTrue(logs)
        self.assertEqual(logs[-1].usuarioId, gerente.id)

    def test_2_login_negado_sem_senha(self):
        resp = self.client.post(
            "/auth/login",
            json={"email": "gerente.a@test.dev", "senha": "senha-errada-123"},
        )
        self.assertEqual(resp.status_code, 401)
        logs = self._logs("LOGIN_NEGADO")
        self.assertTrue(logs)
        texto = json.dumps(
            [logs[-1].dadosAnteriores, logs[-1].dadosNovos], ensure_ascii=False
        )
        self.assertNotIn("senha-errada-123", texto)
        self.assertNotIn("Gerente@123", texto)

    def test_3_auditoria_entrada(self):
        token = self._gerente_token()
        self.client.post(
            "/estoque/entrada",
            json={"unidadeId": self.unidade_a_id, "produtoId": self.produto_id, "quantidade": 5},
            headers=self._headers(token),
        )
        self.assertTrue(self._logs("ESTOQUE_ENTRADA"))

    def test_4_auditoria_saida(self):
        token = self._gerente_token()
        self.client.post(
            "/estoque/saida",
            json={"unidadeId": self.unidade_a_id, "produtoId": self.produto_id, "quantidade": 2},
            headers=self._headers(token),
        )
        self.assertTrue(self._logs("ESTOQUE_SAIDA"))

    def test_5_auditoria_ajuste(self):
        token = self._gerente_token()
        alvo = self._qtd() + 7
        self.client.post(
            "/estoque/ajuste",
            json={"unidadeId": self.unidade_a_id, "produtoId": self.produto_id, "quantidade": alvo},
            headers=self._headers(token),
        )
        self.assertTrue(self._logs("ESTOQUE_AJUSTE"))

    def test_6_auditoria_criacao_pedido(self):
        self._criar_pedido(self._gerente_token())
        logs = self._logs("CRIACAO")
        self.assertTrue(logs)
        self.assertEqual(logs[-1].entidade, "Pedido")

    def test_7_auditoria_alteracao_status(self):
        token = self._gerente_token()
        pedido_id = self._criar_pedido(token).get_json()["id"]
        self.client.patch(
            f"/pedidos/{pedido_id}/status",
            json={"status": "EM_PREPARO"},
            headers=self._headers(token),
        )
        self.assertTrue(self._logs("ALTERACAO_STATUS"))

    def test_8_auditoria_cancelamento(self):
        token = self._gerente_token()
        pedido_id = self._criar_pedido(token).get_json()["id"]
        self.client.post(
            f"/pedidos/{pedido_id}/cancelamento",
            json={},
            headers=self._headers(token),
        )
        self.assertTrue(self._logs("CANCELAMENTO"))

    def test_9_auditoria_pagamento_aprovado(self):
        token = self._gerente_token()
        pedido_id = self._criar_pedido(token).get_json()["id"]
        self.client.post(
            "/pagamentos",
            json={"pedidoId": pedido_id, "metodo": "PIX", "simularResultado": "APROVADO"},
            headers=self._headers(token),
        )
        self.assertTrue(self._logs("PAGAMENTO_APROVADO"))

    def test_10_auditoria_pagamento_recusado(self):
        token = self._gerente_token()
        pedido_id = self._criar_pedido(token).get_json()["id"]
        self.client.post(
            "/pagamentos",
            json={"pedidoId": pedido_id, "metodo": "PIX", "simularResultado": "RECUSADO"},
            headers=self._headers(token),
        )
        self.assertTrue(self._logs("PAGAMENTO_RECUSADO"))

    def test_11_auditoria_resgate_pontos(self):
        with self.app.app_context():
            conta = db.session.scalar(
                select(ContaFidelidade).filter_by(clienteId=self.cliente_id)
            )
            conta.saldoPontos = 50
            db.session.commit()
        token = self._admin_token()
        resp = self.client.post(
            f"/clientes/{self.cliente_id}/fidelidade/resgate",
            json={"pontos": 10},
            headers=self._headers(token),
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(self._logs("RESGATE_PONTOS"))

    def test_12_auditoria_estorno_pontos(self):
        token = self._gerente_token()
        pedido_id = self._criar_pedido(token, cliente_id=self.cliente_id, qty=2).get_json()["id"]
        self.client.post(
            "/pagamentos",
            json={"pedidoId": pedido_id, "metodo": "PIX", "simularResultado": "APROVADO"},
            headers=self._headers(token),
        )
        self.client.post(
            f"/pedidos/{pedido_id}/cancelamento",
            json={},
            headers=self._headers(token),
        )
        self.assertTrue(self._logs("ESTORNO_PONTOS"))

    # ---------- Mascaramento de dados sensiveis ----------

    def _registrar_sensivel(self, dados):
        with self.app.app_context():
            registrar_auditoria(None, "Teste", 1, "TESTE_SENSIVEL", dados_novos=dados)
            db.session.commit()
            log = db.session.scalars(
                select(LogAuditoria)
                .where(LogAuditoria.acao == "TESTE_SENSIVEL")
                .order_by(LogAuditoria.id.desc())
            ).first()
            return log.dadosNovos

    def test_13_auditoria_sem_senha(self):
        guardado = self._registrar_sensivel({"senha": "segredo-123"})
        self.assertEqual(guardado["senha"], "***")
        self.assertNotIn("segredo-123", json.dumps(guardado))

    def test_14_auditoria_sem_senha_hash(self):
        guardado = self._registrar_sensivel({"senhaHash": "hash-abc"})
        self.assertEqual(guardado["senhaHash"], "***")
        self.assertNotIn("hash-abc", json.dumps(guardado))

    def test_15_auditoria_sem_jwt(self):
        guardado = self._registrar_sensivel(
            {"authorization": "Bearer abc", "token": "tok-xyz"}
        )
        self.assertEqual(guardado["authorization"], "***")
        self.assertEqual(guardado["token"], "***")
        self.assertNotIn("tok-xyz", json.dumps(guardado))

    def test_16_auditoria_sem_cartao(self):
        guardado = self._registrar_sensivel(
            {"cvv": "123", "numero_cartao": "4111111111111111"}
        )
        self.assertEqual(guardado["cvv"], "***")
        self.assertEqual(guardado["numero_cartao"], "***")
        self.assertNotIn("4111111111111111", json.dumps(guardado))

    def test_17_rollback_sem_auditoria_orfa(self):
        with self.app.app_context():
            antes = len(
                db.session.scalars(
                    select(LogAuditoria).where(LogAuditoria.acao == "CRIACAO")
                ).all()
            )
            original = pedidos_uc._registrar_historico

            def falha(*_args, **_kwargs):
                raise RuntimeError("falha simulada")

            pedidos_uc._registrar_historico = falha
            try:
                with self.assertRaises(RuntimeError):
                    pedidos_uc.criar_pedido(
                        self.unidade_a_id,
                        "BALCAO",
                        [{"produtoId": self.produto_id, "quantidade": 1}],
                        usuario_id=None,
                    )
            finally:
                pedidos_uc._registrar_historico = original
                db.session.rollback()

            depois = len(
                db.session.scalars(
                    select(LogAuditoria).where(LogAuditoria.acao == "CRIACAO")
                ).all()
            )
            self.assertEqual(depois, antes)

    def test_18_cliente_nao_acessa_outro_cliente(self):
        with self.app.app_context():
            usuario = Usuario(
                nome="Dono Cliente",
                email="dono@test.dev",
                senhaHash=gerar_hash_senha("Dono@123"),
                ativo=True,
            )
            db.session.add(usuario)
            db.session.flush()
            cliente_a = Cliente(
                nome="Cliente A", email="cliente.a@test.dev", usuarioId=usuario.id
            )
            cliente_b = Cliente(nome="Cliente B", email="cliente.b@test.dev")
            db.session.add_all([cliente_a, cliente_b])
            db.session.commit()
            id_a, id_b = cliente_a.id, cliente_b.id

        token = self._token("dono@test.dev", "Dono@123")
        proprio = self.client.get(
            f"/clientes/{id_a}/fidelidade", headers=self._headers(token)
        )
        outro = self.client.get(
            f"/clientes/{id_b}/fidelidade", headers=self._headers(token)
        )
        self.assertEqual(proprio.status_code, 200)
        self.assertEqual(outro.status_code, 403)

    def test_19_anonimizacao(self):
        with self.app.app_context():
            cliente = Cliente(
                nome="Cliente LGPD",
                cpf="111.111.111-11",
                email="lgpd@test.dev",
                telefone="(81) 90000-0000",
            )
            db.session.add(cliente)
            db.session.commit()
            cliente_id = cliente.id

        token = self._admin_token()
        resp = self.client.post(
            f"/clientes/{cliente_id}/anonimizacao", headers=self._headers(token)
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["nome"], "ANONIMIZADO")

        with self.app.app_context():
            cliente = db.session.get(Cliente, cliente_id)
            self.assertTrue(cliente.anonimizado)
            self.assertIsNone(cliente.cpf)
            self.assertIsNone(cliente.email)
            self.assertIsNone(cliente.telefone)
            self.assertIsNone(cliente.dataNascimento)
        self.assertTrue(self._logs("ANONIMIZACAO"))


if __name__ == "__main__":
    unittest.main()
