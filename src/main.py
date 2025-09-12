# src/main.py
import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# ------------------------------------------------------------------------------
# App + Config
# ------------------------------------------------------------------------------
app = Flask(__name__, static_folder="static", static_url_path="/")

# Allow all origins for now (tighten later to your Vercel domain if you prefer)
CORS(app, resources={r"/api/*": {"origins": "*"}, r"/health": {"origins": "*"}})

# Database config: prefer DATABASE_URL; else writable SQLite in /tmp
DB_URL = (os.environ.get("DATABASE_URL") or "").strip()
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)
if not DB_URL:
    DB_URL = "sqlite:////tmp/metier.db"  # always writable in containers

app.config["SQLALCHEMY_DATABASE_URI"] = DB_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ------------------------------------------------------------------------------
# Optional: try to import models so db.create_all() can create tables if defined
# If imports fail (circular import, path differences, etc.), we keep running.
# ------------------------------------------------------------------------------
try:
    # If your model modules exist, import them so metadata is registered
    import models.product  # noqa: F401
    import models.order    # noqa: F401
    import models.user     # noqa: F401
    print("[info] models imported for create_all()")
except Exception as e:
    print(f"[warn] could not import models (continuing without): {e}")

# Create tables (if models were successfully imported)
with app.app_context():
    try:
        db.create_all()
        print("[info] db.create_all() completed (if models present)")
    except Exception as e:
        print(f"[warn] db.create_all() failed (continuing): {e}")

# ------------------------------------------------------------------------------
# Health + Root
# ------------------------------------------------------------------------------
@app.get("/health")
def health():
    return jsonify(ok=True), 200

@app.get("/")
def root():
    return jsonify(status="ok", service="metier-backend"), 200

# ------------------------------------------------------------------------------
# Fallback Products API (works even if blueprints/models aren't wired yet)
# - Tries to read from a table named `products` using a safe text query.
# - If the table doesn't exist yet, returns [].
# ------------------------------------------------------------------------------
@app.get("/api/products")
def api_products():
    try:
        # Try to fetch some columns commonly present; fall back to SELECT * if needed
        sql = text("SELECT * FROM products LIMIT 50")
        rows = db.session.execute(sql).mappings().all()  # mappings() => dict-like rows
        return jsonify([dict(r) for r in rows]), 200
    except SQLAlchemyError as e:
        msg = str(e)
        # If products table doesn't exist yet, just return empty list so the app works
        if "no such table" in msg or "relation \"products\" does not exist" in msg:
            return jsonify([]), 200
        return jsonify(error=type(e).__name__, message=msg), 500
    except Exception as e:
        return jsonify(error="ServerError", message=str(e)), 500

# ------------------------------------------------------------------------------
# Entrypoint (bind to Railway's PORT)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
