import os
import tempfile
import unittest

_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = "sqlite:///" + _db_path.replace("\\", "/")
os.environ["JWT_SECRET_KEY"] = "chave-jwt-de-teste-com-32-bytes-ou-mais-123456"

from app import create_app
from app.infrastructure.auth.passwords import gerar_hash_senha
from app.infrastructure.database import db
from app.infrastructure.database.models import (
    Estoque,
    MovimentacaoEstoque,
    Papel,
    Produto,
    Unidade,
    Usuario,
    UsuarioPapel,
)
from app.infrastructure.database.seeds.seed import run_seed


class EstoqueTestCase(unittest.TestCase):
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
            cls.produto_id = Produto.query.filter_by(nome="Suco de Caja").first().id

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

    def _post(self, rota, token, payload):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return self.client.post(rota, json=payload, headers=headers)

    def _qtd(self, unidade_id, produto_id):
        with self.app.app_context():
            estoque = Estoque.query.filter_by(
                unidadeId=unidade_id, produtoId=produto_id
            ).first()
            return estoque.quantidadeAtual if estoque else None

    def _mov_count(self, unidade_id, produto_id):
        with self.app.app_context():
            estoque = Estoque.query.filter_by(
                unidadeId=unidade_id, produtoId=produto_id
            ).first()
            return MovimentacaoEstoque.query.filter_by(estoqueId=estoque.id).count()

    def _gerente_token(self):
        return self._token("gerente.a@test.dev", "Gerente@123")

    def test_1_entrada_valida(self):
        token = self._gerente_token()
        antes = self._qtd(self.unidade_a_id, self.produto_id)
        resp = self._post(
            "/estoque/entrada",
            token,
            {
                "unidadeId": self.unidade_a_id,
                "produtoId": self.produto_id,
                "quantidade": 10,
                "motivo": "teste entrada",
            },
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(self._qtd(self.unidade_a_id, self.produto_id), antes + 10)

    def test_2_saida_valida(self):
        token = self._gerente_token()
        antes = self._qtd(self.unidade_a_id, self.produto_id)
        resp = self._post(
            "/estoque/saida",
            token,
            {
                "unidadeId": self.unidade_a_id,
                "produtoId": self.produto_id,
                "quantidade": 5,
                "motivo": "teste saida",
            },
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(self._qtd(self.unidade_a_id, self.produto_id), antes - 5)

    def test_3_saida_maior_que_estoque(self):
        token = self._gerente_token()
        antes = self._qtd(self.unidade_a_id, self.produto_id)
        resp = self._post(
            "/estoque/saida",
            token,
            {
                "unidadeId": self.unidade_a_id,
                "produtoId": self.produto_id,
                "quantidade": 999999,
            },
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "estoque_insuficiente")
        self.assertEqual(self._qtd(self.unidade_a_id, self.produto_id), antes)

    def test_4_quantidade_invalida(self):
        token = self._gerente_token()
        for quantidade in (0, -3):
            resp = self._post(
                "/estoque/entrada",
                token,
                {
                    "unidadeId": self.unidade_a_id,
                    "produtoId": self.produto_id,
                    "quantidade": quantidade,
                },
            )
            self.assertEqual(resp.status_code, 422)
            self.assertEqual(resp.get_json()["erro"]["codigo"], "dados_invalidos")

    def test_5_produto_inexistente(self):
        token = self._gerente_token()
        resp = self._post(
            "/estoque/entrada",
            token,
            {
                "unidadeId": self.unidade_a_id,
                "produtoId": 999999,
                "quantidade": 1,
            },
        )
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "nao_encontrado")

    def test_6_unidade_inexistente(self):
        token = self._token("admin@raizes.dev", "Admin@123")
        resp = self._post(
            "/estoque/entrada",
            token,
            {
                "unidadeId": 999999,
                "produtoId": self.produto_id,
                "quantidade": 1,
            },
        )
        self.assertEqual(resp.status_code, 404)

    def test_7_usuario_sem_permissao(self):
        token = self._token("atendente@raizes.dev", "Atendente@123")
        resp = self._post(
            "/estoque/entrada",
            token,
            {
                "unidadeId": self.unidade_a_id,
                "produtoId": self.produto_id,
                "quantidade": 1,
            },
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "acesso_negado")

    def test_8_sem_jwt(self):
        resp = self._post(
            "/estoque/entrada",
            None,
            {
                "unidadeId": self.unidade_a_id,
                "produtoId": self.produto_id,
                "quantidade": 1,
            },
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "token_ausente")

    def test_9_movimentacao_criada_apos_entrada(self):
        token = self._gerente_token()
        antes = self._mov_count(self.unidade_a_id, self.produto_id)
        resp = self._post(
            "/estoque/entrada",
            token,
            {
                "unidadeId": self.unidade_a_id,
                "produtoId": self.produto_id,
                "quantidade": 4,
            },
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["movimentacao"]["tipo"], "ENTRADA")
        self.assertEqual(self._mov_count(self.unidade_a_id, self.produto_id), antes + 1)

    def test_10_movimentacao_criada_apos_saida(self):
        token = self._gerente_token()
        antes = self._mov_count(self.unidade_a_id, self.produto_id)
        resp = self._post(
            "/estoque/saida",
            token,
            {
                "unidadeId": self.unidade_a_id,
                "produtoId": self.produto_id,
                "quantidade": 2,
            },
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["movimentacao"]["tipo"], "SAIDA")
        self.assertEqual(self._mov_count(self.unidade_a_id, self.produto_id), antes + 1)

    def test_11_quantidade_final_correta(self):
        token = self._gerente_token()
        inicial = self._qtd(self.unidade_a_id, self.produto_id)
        self._post(
            "/estoque/entrada",
            token,
            {
                "unidadeId": self.unidade_a_id,
                "produtoId": self.produto_id,
                "quantidade": 7,
            },
        )
        self._post(
            "/estoque/saida",
            token,
            {
                "unidadeId": self.unidade_a_id,
                "produtoId": self.produto_id,
                "quantidade": 3,
            },
        )
        self.assertEqual(self._qtd(self.unidade_a_id, self.produto_id), inicial + 4)

    def test_12_outra_unidade_negada(self):
        token = self._gerente_token()
        resp = self._post(
            "/estoque/entrada",
            token,
            {
                "unidadeId": self.unidade_b_id,
                "produtoId": self.produto_id,
                "quantidade": 1,
            },
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "acesso_negado")


if __name__ == "__main__":
    unittest.main()
