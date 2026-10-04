from app.api.routes.auth import auth_bp
from app.api.routes.dev import dev_bp
from app.api.routes.estoque import estoque_bp
from app.api.routes.fidelidade import fidelidade_bp
from app.api.routes.pagamentos import pagamentos_bp
from app.api.routes.pedidos import pedidos_bp


def registrar_rotas(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(dev_bp)
    app.register_blueprint(estoque_bp)
    app.register_blueprint(pedidos_bp)
    app.register_blueprint(pagamentos_bp)
    app.register_blueprint(fidelidade_bp)
