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
from app.infrastructure.database.models import Papel, Usuario, UsuarioPapel
from app.infrastructure.database.seeds.seed import run_seed


class RBACTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            db.create_all()
            run_seed()

            papel_gerente = Papel.query.filter_by(nome="GERENTE").first()
            gerente = Usuario(
                nome="Gerente Teste",
                email="gerente@test.dev",
                senhaHash=gerar_hash_senha("Gerente@123"),
                ativo=True,
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

    def _get(self, rota, token=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return self.client.get(rota, headers=headers)

    def test_1_admin_permissao_permitida(self):
        token = self._token("admin@raizes.dev", "Admin@123")
        resp = self._get("/dev/rbac/estoque-ajustar", token)
        self.assertEqual(resp.status_code, 200)

    def test_2_atendente_permissao_permitida(self):
        token = self._token("atendente@raizes.dev", "Atendente@123")
        resp = self._get("/dev/rbac/pedido-cancelar", token)
        self.assertEqual(resp.status_code, 200)

    def test_3_atendente_permissao_negada(self):
        token = self._token("atendente@raizes.dev", "Atendente@123")
        resp = self._get("/dev/rbac/estoque-ajustar", token)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "acesso_negado")

    def test_4_gerente_permissao_permitida(self):
        token = self._token("gerente@test.dev", "Gerente@123")
        resp = self._get("/dev/rbac/produto-gerenciar", token)
        self.assertEqual(resp.status_code, 200)

    def test_5_sem_jwt(self):
        resp = self._get("/dev/rbac/estoque-ajustar")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "token_ausente")

    def test_6_jwt_valido_sem_permissao(self):
        token = self._token("gerente@test.dev", "Gerente@123")
        resp = self._get("/dev/rbac/usuario-gerenciar", token)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "acesso_negado")


if __name__ == "__main__":
    unittest.main()
