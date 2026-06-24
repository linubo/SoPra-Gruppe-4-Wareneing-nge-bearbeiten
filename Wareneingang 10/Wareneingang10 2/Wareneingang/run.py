from pathlib import Path
from dotenv import load_dotenv

# Lokale .env laden
load_dotenv()

# Render Secret File laden, falls vorhanden
render_env = Path("/etc/secrets/.env")
if render_env.exists():
    load_dotenv(render_env)

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)