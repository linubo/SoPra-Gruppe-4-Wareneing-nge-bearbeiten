import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

# Lokale .env laden
load_dotenv()

# Render Secret File laden, falls du statt Environment Variables eine .env-Datei nutzt
render_env = Path("/etc/secrets/.env")
if render_env.exists():
    load_dotenv(render_env)

from app.auth import auth_template_context
from app.routes.db_status_routes import db_status_bp


def format_money(value):
    try:
        numeric_value = float(str(value).replace(",", "."))

    except (TypeError, ValueError):
        return value

    formatted_value = f"{numeric_value:,.2f}"
    return formatted_value.replace(",", "X").replace(".", ",").replace("X", ".")


def format_date_only(value):
    if value is None:
        return ""

    date_value = str(value).split(" ")[0]
    parts = date_value.split("-")

    if len(parts) == 3:
        return f"{parts[2]}.{parts[1]}.{parts[0]}"

    return date_value


def create_app():
    app = Flask(__name__)

    # Secret Key für Flask
    app.config["SECRET_KEY"] = os.getenv(
        "FLASK_SECRET_KEY",
        os.getenv("SECRET_KEY", "dev-secret-key")
    )

    # Datenbank-Konfiguration
    app.config["DB_SERVER"] = os.getenv("DB_SERVER")
    app.config["DB_NAME"] = os.getenv("DB_NAME")
    app.config["DB_USER"] = os.getenv("DB_USER")
    app.config["DB_PASSWORD"] = os.getenv("DB_PASSWORD")
    app.config["DB_DRIVER"] = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    app.config["DB_PORT"] = os.getenv("DB_PORT", "1433")
    app.config["DB_ENCRYPT"] = os.getenv("DB_ENCRYPT", "yes")
    app.config["DB_TRUST_SERVER_CERTIFICATE"] = os.getenv(
        "DB_TRUST_SERVER_CERTIFICATE",
        "yes"
    )

    # Kleiner Check für Render-Logs
    required_db_vars = ["DB_SERVER", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing_vars = [var for var in required_db_vars if not app.config.get(var)]

    if missing_vars:
        print(f"Warnung: Folgende DB-Variablen fehlen: {', '.join(missing_vars)}")
    else:
        print("DB-Variablen wurden geladen.")

    # Wird später z. B. für Flash-Meldungen/Formulare gebraucht
    app.context_processor(auth_template_context)
    app.jinja_env.filters["money"] = format_money
    app.jinja_env.filters["date_only"] = format_date_only

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
