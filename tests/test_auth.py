import os
import tempfile
import unittest
from datetime import timedelta

_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = "sqlite:///" + _db_path.replace("\\", "/")
os.environ["JWT_SECRET_KEY"] = "chave-jwt-de-teste-com-32-bytes-ou-mais-123456"

from flask_jwt_extended import create_access_token

from app import create_app
from app.infrastructure.auth.passwords import gerar_hash_senha
from app.infrastructure.database import db
from app.infrastructure.database.models import Usuario

SENHA_VALIDA = "SenhaCorreta1"


class AuthTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            db.create_all()
            ativo = Usuario(
                nome="Usuario Ativo",
                email="ativo@test.dev",
                senhaHash=gerar_hash_senha(SENHA_VALIDA),
                ativo=True,
            )
            inativo = Usuario(
                nome="Usuario Inativo",
                email="inativo@test.dev",
                senhaHash=gerar_hash_senha(SENHA_VALIDA),
                ativo=False,
            )
            db.session.add_all([ativo, inativo])
            db.session.commit()
            cls.ativo_id = ativo.id

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        if os.path.exists(_db_path):
            os.remove(_db_path)

    def _login(self, email, senha):
        return self.client.post("/auth/login", json={"email": email, "senha": senha})

    def test_1_login_valido(self):
        resp = self._login("ativo@test.dev", SENHA_VALIDA)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access_token", resp.get_json())

    def test_2_login_senha_incorreta(self):
        resp = self._login("ativo@test.dev", "senha-errada")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "credenciais_invalidas")

    def test_3_login_usuario_inexistente(self):
        resp = self._login("ninguem@test.dev", SENHA_VALIDA)
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "credenciais_invalidas")

    def test_4_login_usuario_inativo(self):
        resp = self._login("inativo@test.dev", SENHA_VALIDA)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "usuario_inativo")

    def test_5_me_com_token_valido(self):
        token = self._login("ativo@test.dev", SENHA_VALIDA).get_json()["access_token"]
        resp = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(resp.status_code, 200)
        corpo = resp.get_json()
        self.assertEqual(corpo["email"], "ativo@test.dev")
        self.assertNotIn("senhaHash", corpo)
        self.assertNotIn("senha", corpo)

    def test_6_me_sem_token(self):
        resp = self.client.get("/auth/me")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "token_ausente")

    def test_7_me_token_invalido(self):
        resp = self.client.get(
            "/auth/me", headers={"Authorization": "Bearer token.invalido.aqui"}
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "token_invalido")

    def test_8_me_token_expirado(self):
        with self.app.app_context():
            token = create_access_token(
                identity=str(self.ativo_id),
                expires_delta=timedelta(seconds=-1),
            )
        resp = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["erro"]["codigo"], "token_expirado")


if __name__ == "__main__":
    unittest.main()
