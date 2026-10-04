import os
import tempfile
import unittest

_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = "sqlite:///" + _db_path.replace("\\", "/")
os.environ["JWT_SECRET_KEY"] = "chave-jwt-de-teste-com-32-bytes-ou-mais-123456"

from app import create_app
from app.infrastructure.database import db


class DocsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.engine.dispose()
        if os.path.exists(_db_path):
            os.remove(_db_path)

    def test_1_swagger_ui_disponivel(self):
        resp = self.client.get("/docs/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp.content_type)

    def test_2_openapi_json_gerado(self):
        resp = self.client.get("/apispec_1.json")
        self.assertEqual(resp.status_code, 200)
        spec = resp.get_json()
        self.assertEqual(spec["swagger"], "2.0")
        caminhos = spec["paths"]
        for rota in (
            "/auth/login",
            "/auth/me",
            "/estoque",
            "/pedidos",
            "/pedidos/{id}/status",
            "/pedidos/{id}/cancelamento",
            "/pagamentos",
            "/clientes/{id}/fidelidade",
        ):
            self.assertIn(rota, caminhos)

    def test_3_esquema_jwt_e_erro_json(self):
        spec = self.client.get("/apispec_1.json").get_json()
        self.assertIn("Bearer", spec["securityDefinitions"])
        self.assertEqual(
            spec["securityDefinitions"]["Bearer"]["name"], "Authorization"
        )
        self.assertIn("ErrorResponse", spec["definitions"])


if __name__ == "__main__":
    unittest.main()
