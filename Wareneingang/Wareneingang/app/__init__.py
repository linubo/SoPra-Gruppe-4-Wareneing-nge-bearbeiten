import os

from flask import Flask

from app.auth import auth_template_context
from app.routes.db_status_routes import db_status_bp

def create_app():
    app = Flask(__name__)

    # Wird später z. B. für Flash-Meldungen/Formulare gebraucht
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
    app.context_processor(auth_template_context)

    # Routen importieren
    from app.routes.auth_routes import auth_bp
    from app.routes.dashboard_routes import dashboard_bp
    from app.routes.goods_receipt_routes import goods_receipt_bp
    from app.routes.supplier_invoice_routes import supplier_invoice_bp

    # Routen registrieren
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(goods_receipt_bp)
    app.register_blueprint(supplier_invoice_bp)
    app.register_blueprint(db_status_bp)

    return app
