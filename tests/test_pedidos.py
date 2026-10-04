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
    Categoria,
    Estoque,
    HistoricoStatusPedido,
    ItemPedido,
    MovimentacaoEstoque,
    Papel,
    Pedido,
    Produto,
    Unidade,
    Usuario,
    UsuarioPapel,
)
from app.infrastructure.database.seeds.seed import run_seed


class PedidosTestCase(unittest.TestCase):
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

            produto1 = Produto.query.filter_by(nome="Suco de Caja").first()
            cls.produto1_id = produto1.id
            cls.preco1 = produto1.precoBase

            categoria = Categoria.query.filter_by(nome="Bebidas").first()
            inativo = Produto(
                nome="Refri Inativo (TESTE)",
                precoBase=Decimal("5.00"),
                categoriaId=categoria.id,
                ativo=False,
            )
            db.session.add(inativo)
            db.session.flush()
            cls.produto_inativo_id = inativo.id

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

            sem_papel = Usuario(
                nome="Sem Papel",
                email="sempapel@test.dev",
                senhaHash=gerar_hash_senha("SemPapel@123"),
                ativo=True,
                unidadeId=unidade_a.id,
            )
            db.session.add(sem_papel)
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

    def _headers(self, token):
        return {"Authorization": f"Bearer {token}"} if token else {}

    def _gerente_token(self):
        return self._token("gerente.a@test.dev", "Gerente@123")

    def _admin_token(self):
        return self._token("admin@raizes.dev", "Admin@123")

    def _criar(self, token, **over):
        payload = {
            "unidadeId": self.unidade_a_id,
            "canalPedido": "BALCAO",
            "itens": [{"produtoId": self.produto1_id, "quantidade": 2}],
        }
        payload.update(over)
        return self.client.post("/pedidos", json=payload, headers=self._headers(token))

    def _qtd(self, unidade_id, produto_id):
        with self.app.app_context():
            estoque = db.session.scalar(
                select(Estoque).filter_by(unidadeId=unidade_id, produtoId=produto_id)
            )
            return estoque.quantidadeAtual if estoque else None

    def _mov_saida(self, pedido_id):
        with self.app.app_context():
            return db.session.scalars(
                select(MovimentacaoEstoque).where(
                    MovimentacaoEstoque.pedidoId == pedido_id,
                    MovimentacaoEstoque.tipo == "SAIDA",
                )
            ).all()

    def _mov_entrada(self, pedido_id):
        with self.app.app_context():
            return db.session.scalars(
                select(MovimentacaoEstoque).where(
                    MovimentacaoEstoque.pedidoId == pedido_id,
                    MovimentacaoEstoque.tipo == "ENTRADA",
                )
            ).all()

    def _historico(self, pedido_id):
        with self.app.app_context():
            return db.session.scalars(
                select(HistoricoStatusPedido)
                .where(HistoricoStatusPedido.pedidoId == pedido_id)
                .order_by(HistoricoStatusPedido.id)
            ).all()

    # ---------- Criacao ----------

    def test_1_criacao_valida(self):
        resp = self._criar(self._gerente_token())
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["status"], "RECEBIDO")

    def test_2_canal_ausente(self):
        token = self._gerente_token()
        resp = self.client.post(
            "/pedidos",
            json={
                "unidadeId": self.unidade_a_id,
                "itens": [{"produtoId": self.produto1_id, "quantidade": 1}],
            },
            headers=self._headers(token),
        )
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "dados_invalidos")

    def test_3_canal_invalido(self):
        resp = self._criar(self._gerente_token(), canalPedido="DRIVE")
        self.assertEqual(resp.status_code, 422)

    def test_4_produto_inexistente(self):
        resp = self._criar(
            self._gerente_token(),
            itens=[{"produtoId": 999999, "quantidade": 1}],
        )
        self.assertEqual(resp.status_code, 404)

    def test_5_produto_inativo(self):
        resp = self._criar(
            self._gerente_token(),
            itens=[{"produtoId": self.produto_inativo_id, "quantidade": 1}],
        )
        self.assertEqual(resp.status_code, 422)

    def test_6_cliente_inexistente(self):
        resp = self._criar(self._gerente_token(), clienteId=999999)
        self.assertEqual(resp.status_code, 404)

    def test_7_quantidade_zero(self):
        resp = self._criar(
            self._gerente_token(),
            itens=[{"produtoId": self.produto1_id, "quantidade": 0}],
        )
        self.assertEqual(resp.status_code, 422)

    def test_8_quantidade_negativa(self):
        resp = self._criar(
            self._gerente_token(),
            itens=[{"produtoId": self.produto1_id, "quantidade": -2}],
        )
        self.assertEqual(resp.status_code, 422)

    def test_9_quantidade_nao_inteira(self):
        resp = self._criar(
            self._gerente_token(),
            itens=[{"produtoId": self.produto1_id, "quantidade": 1.5}],
        )
        self.assertEqual(resp.status_code, 422)

    def test_10_estoque_insuficiente(self):
        resp = self._criar(
            self._gerente_token(),
            itens=[{"produtoId": self.produto1_id, "quantidade": 999999}],
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "estoque_insuficiente")

    def test_11_criacao_estoque_suficiente_baixa(self):
        token = self._gerente_token()
        antes = self._qtd(self.unidade_a_id, self.produto1_id)
        resp = self._criar(
            token, itens=[{"produtoId": self.produto1_id, "quantidade": 3}]
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(self._qtd(self.unidade_a_id, self.produto1_id), antes - 3)

    def test_12_valor_unitario_servidor(self):
        resp = self._criar(
            self._gerente_token(),
            valorTotal="0.01",
            itens=[
                {
                    "produtoId": self.produto1_id,
                    "quantidade": 2,
                    "valorUnitario": "0.01",
                }
            ],
        )
        item = resp.get_json()["itens"][0]
        self.assertEqual(item["valorUnitario"], str(self.preco1))

    def test_13_valor_total_item_servidor(self):
        resp = self._criar(
            self._gerente_token(),
            itens=[{"produtoId": self.produto1_id, "quantidade": 2}],
        )
        item = resp.get_json()["itens"][0]
        self.assertEqual(item["valorTotalItem"], str(self.preco1 * 2))

    def test_14_valor_total_pedido_servidor(self):
        resp = self._criar(
            self._gerente_token(),
            itens=[{"produtoId": self.produto1_id, "quantidade": 2}],
        )
        corpo = resp.get_json()
        self.assertEqual(corpo["valorProdutos"], str(self.preco1 * 2))
        self.assertEqual(corpo["valorDesconto"], "0.00")
        self.assertEqual(corpo["valorTotal"], str(self.preco1 * 2))

    def test_15_movimentacao_saida_criada(self):
        token = self._gerente_token()
        pedido_id = self._criar(token).get_json()["id"]
        self.assertEqual(len(self._mov_saida(pedido_id)), 1)

    def test_16_movimentacao_vinculada_ao_pedido(self):
        token = self._gerente_token()
        pedido_id = self._criar(token).get_json()["id"]
        movimentos = self._mov_saida(pedido_id)
        self.assertTrue(all(m.pedidoId == pedido_id for m in movimentos))

    def test_17_historico_inicial_criado(self):
        token = self._gerente_token()
        pedido_id = self._criar(token).get_json()["id"]
        historico = self._historico(pedido_id)
        self.assertEqual(len(historico), 1)
        self.assertIsNone(historico[0].statusAnterior)
        self.assertEqual(historico[0].statusNovo, "RECEBIDO")

    # ---------- Consultas ----------

    def test_18_listar_pedidos(self):
        resp = self.client.get("/pedidos", headers=self._headers(self._gerente_token()))
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.get_json(), list)

    def test_19_consultar_por_id(self):
        token = self._gerente_token()
        pedido_id = self._criar(token).get_json()["id"]
        resp = self.client.get(
            f"/pedidos/{pedido_id}", headers=self._headers(token)
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["id"], pedido_id)
        self.assertIn("itens", resp.get_json())

    def test_20_consultar_inexistente(self):
        resp = self.client.get(
            "/pedidos/999999", headers=self._headers(self._gerente_token())
        )
        self.assertEqual(resp.status_code, 404)

    def test_21_filtrar_canal(self):
        token = self._gerente_token()
        self._criar(token, canalPedido="TOTEM")
        resp = self.client.get(
            "/pedidos?canalPedido=TOTEM", headers=self._headers(token)
        )
        self.assertEqual(resp.status_code, 200)
        lista = resp.get_json()
        self.assertTrue(lista)
        self.assertTrue(all(p["canalPedido"] == "TOTEM" for p in lista))

    def test_22_filtrar_status(self):
        token = self._gerente_token()
        pedido_id = self._criar(token).get_json()["id"]
        self.client.patch(
            f"/pedidos/{pedido_id}/status",
            json={"status": "EM_PREPARO"},
            headers=self._headers(token),
        )
        resp = self.client.get(
            "/pedidos?status=EM_PREPARO", headers=self._headers(token)
        )
        lista = resp.get_json()
        self.assertTrue(lista)
        self.assertTrue(all(p["status"] == "EM_PREPARO" for p in lista))

    # ---------- Status ----------

    def _criar_e_mudar(self, token, *statuses):
        pedido_id = self._criar(token).get_json()["id"]
        for status in statuses:
            self.client.patch(
                f"/pedidos/{pedido_id}/status",
                json={"status": status},
                headers=self._headers(token),
            )
        return pedido_id

    def test_23_recebido_para_em_preparo(self):
        token = self._gerente_token()
        pedido_id = self._criar(token).get_json()["id"]
        resp = self.client.patch(
            f"/pedidos/{pedido_id}/status",
            json={"status": "EM_PREPARO"},
            headers=self._headers(token),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "EM_PREPARO")

    def test_24_em_preparo_para_pronto(self):
        token = self._gerente_token()
        pedido_id = self._criar_e_mudar(token, "EM_PREPARO")
        resp = self.client.patch(
            f"/pedidos/{pedido_id}/status",
            json={"status": "PRONTO"},
            headers=self._headers(token),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "PRONTO")

    def test_25_pronto_para_concluido(self):
        token = self._gerente_token()
        pedido_id = self._criar_e_mudar(token, "EM_PREPARO", "PRONTO")
        resp = self.client.patch(
            f"/pedidos/{pedido_id}/status",
            json={"status": "CONCLUIDO"},
            headers=self._headers(token),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "CONCLUIDO")

    def test_26_voltar_status_anterior(self):
        token = self._gerente_token()
        pedido_id = self._criar_e_mudar(token, "EM_PREPARO")
        resp = self.client.patch(
            f"/pedidos/{pedido_id}/status",
            json={"status": "RECEBIDO"},
            headers=self._headers(token),
        )
        self.assertEqual(resp.status_code, 409)

    def test_27_pular_etapa(self):
        token = self._gerente_token()
        pedido_id = self._criar(token).get_json()["id"]
        resp = self.client.patch(
            f"/pedidos/{pedido_id}/status",
            json={"status": "PRONTO"},
            headers=self._headers(token),
        )
        self.assertEqual(resp.status_code, 409)

    def test_28_alterar_concluido(self):
        token = self._gerente_token()
        pedido_id = self._criar_e_mudar(token, "EM_PREPARO", "PRONTO", "CONCLUIDO")
        resp = self.client.patch(
            f"/pedidos/{pedido_id}/status",
            json={"status": "EM_PREPARO"},
            headers=self._headers(token),
        )
        self.assertEqual(resp.status_code, 409)

    def test_29_historico_apos_transicao(self):
        token = self._gerente_token()
        pedido_id = self._criar(token).get_json()["id"]
        self.client.patch(
            f"/pedidos/{pedido_id}/status",
            json={"status": "EM_PREPARO", "observacao": "iniciado"},
            headers=self._headers(token),
        )
        historico = self._historico(pedido_id)
        self.assertEqual(len(historico), 2)
        self.assertEqual(historico[1].statusAnterior, "RECEBIDO")
        self.assertEqual(historico[1].statusNovo, "EM_PREPARO")
        self.assertEqual(historico[1].observacao, "iniciado")

    # ---------- Cancelamento ----------

    def _cancelar(self, token, pedido_id, observacao=None):
        return self.client.post(
            f"/pedidos/{pedido_id}/cancelamento",
            json={"observacao": observacao},
            headers=self._headers(token),
        )

    def test_30_cancelar_permitido(self):
        token = self._gerente_token()
        pedido_id = self._criar(token).get_json()["id"]
        resp = self._cancelar(token, pedido_id, "desistiu")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "CANCELADO")

    def test_31_cancelar_concluido(self):
        token = self._gerente_token()
        pedido_id = self._criar_e_mudar(token, "EM_PREPARO", "PRONTO", "CONCLUIDO")
        resp = self._cancelar(token, pedido_id)
        self.assertEqual(resp.status_code, 409)

    def test_32_cancelar_ja_cancelado(self):
        token = self._gerente_token()
        pedido_id = self._criar(token).get_json()["id"]
        self._cancelar(token, pedido_id)
        resp = self._cancelar(token, pedido_id)
        self.assertEqual(resp.status_code, 409)

    def test_33_estoque_devolvido(self):
        token = self._gerente_token()
        inicial = self._qtd(self.unidade_a_id, self.produto1_id)
        pedido_id = self._criar(
            token, itens=[{"produtoId": self.produto1_id, "quantidade": 4}]
        ).get_json()["id"]
        self.assertEqual(self._qtd(self.unidade_a_id, self.produto1_id), inicial - 4)
        self._cancelar(token, pedido_id)
        self.assertEqual(self._qtd(self.unidade_a_id, self.produto1_id), inicial)

    def test_34_movimentacao_entrada_no_cancelamento(self):
        token = self._gerente_token()
        pedido_id = self._criar(token).get_json()["id"]
        self._cancelar(token, pedido_id)
        self.assertEqual(len(self._mov_entrada(pedido_id)), 1)

    def test_35_historico_cancelamento(self):
        token = self._gerente_token()
        pedido_id = self._criar(token).get_json()["id"]
        self._cancelar(token, pedido_id, "cliente desistiu")
        historico = self._historico(pedido_id)
        ultimo = historico[-1]
        self.assertEqual(ultimo.statusNovo, "CANCELADO")
        self.assertEqual(ultimo.observacao, "cliente desistiu")

    def test_36_rollback_falha_cancelamento(self):
        token = self._gerente_token()
        pedido_id = self._criar(
            token, itens=[{"produtoId": self.produto1_id, "quantidade": 3}]
        ).get_json()["id"]
        qtd_pos_criacao = self._qtd(self.unidade_a_id, self.produto1_id)

        with self.app.app_context():
            import app.application.use_cases.pedidos as uc

            original = uc._registrar_historico

            def falha(*_args, **_kwargs):
                raise RuntimeError("falha simulada")

            uc._registrar_historico = falha
            try:
                with self.assertRaises(RuntimeError):
                    uc.cancelar_pedido(pedido_id, usuario_id=None, observacao="x")
            finally:
                uc._registrar_historico = original
                db.session.rollback()

            pedido = db.session.get(Pedido, pedido_id)
            estoque = db.session.scalar(
                select(Estoque).filter_by(
                    unidadeId=self.unidade_a_id, produtoId=self.produto1_id
                )
            )
            self.assertEqual(pedido.status, "RECEBIDO")
            self.assertEqual(estoque.quantidadeAtual, qtd_pos_criacao)

    # ---------- Seguranca / unidade ----------

    def test_37_sem_jwt(self):
        resp = self.client.post(
            "/pedidos",
            json={
                "unidadeId": self.unidade_a_id,
                "canalPedido": "BALCAO",
                "itens": [{"produtoId": self.produto1_id, "quantidade": 1}],
            },
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "token_ausente")

    def test_38_usuario_sem_permissao_status(self):
        token = self._token("sempapel@test.dev", "SemPapel@123")
        pedido_id = self._criar(self._gerente_token()).get_json()["id"]
        resp = self.client.patch(
            f"/pedidos/{pedido_id}/status",
            json={"status": "EM_PREPARO"},
            headers=self._headers(token),
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "acesso_negado")

    def test_39_pedido_de_outra_unidade(self):
        admin = self._admin_token()
        pedido_b = self.client.post(
            "/pedidos",
            json={
                "unidadeId": self.unidade_b_id,
                "canalPedido": "WEB",
                "itens": [{"produtoId": self.produto1_id, "quantidade": 1}],
            },
            headers=self._headers(admin),
        ).get_json()["id"]

        gerente = self._gerente_token()
        resp = self.client.get(
            f"/pedidos/{pedido_b}", headers=self._headers(gerente)
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "acesso_negado")


if __name__ == "__main__":
    unittest.main()
