# src/main.py
import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
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
# Models import (so metadata is known before create_all)
# Adjust these imports to match your repo structure if needed
# ------------------------------------------------------------------------------
try:
    from models.product import Product  # noqa: F401
    from models.order import Order      # noqa: F401
    from models.user import User        # noqa: F401
except Exception as e:
    print(f"[warn] Could not import one or more models: {e}")

# Create tables safely inside an app context
with app.app_context():
    try:
        db.create_all()
        print("[info] db.create_all() completed")
    except Exception as e:
        print(f"[warn] db.create_all() failed: {e}")

# ------------------------------------------------------------------------------
# Optional blueprint registration (register only if present)
# Expects product_bp, cart_bp, order_bp, user_bp, admin_bp in routes/*
# ------------------------------------------------------------------------------
def _maybe_register(module_name: str, bp_name: str):
    try:
        mod = __import__(f"routes.{module_name}", fromlist=[bp_name])
        bp = getattr(mod, bp_name, None)
        if bp is not None:
            app.register_blueprint(bp)
            print(f"[info] Registered blueprint: {module_name}.{bp_name}")
        else:
            print(f"[info] No blueprint named {bp_name} in routes.{module_name}")
    except Exception as e:
        print(f"[info] Blueprint not registered ({module_name}.{bp_name}): {e}")

_maybe_register("product", "product_bp")
_maybe_register("cart", "cart_bp")
_maybe_register("order", "order_bp")
_maybe_register("user", "user_bp")
_maybe_register("admin", "admin_bp")

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
# Fallback Products API (works even if blueprints aren't wired yet)
# ------------------------------------------------------------------------------
def _model_to_dict(m):
    return {c.name: getattr(m, c.name) for c in m.__table__.columns}

@app.get("/api/products")
def api_products():
    try:
        # Limit to something sane for a simple smoke test
        items = Product.query.limit(50).all()
        return jsonify([_model_to_dict(p) for p in items]), 200
    except SQLAlchemyError as e:
        return jsonify(error=type(e).__name__, message=str(e)), 500
    except Exception as e:
        return jsonify(error="ServerError", message=str(e)), 500

# ------------------------------------------------------------------------------
# Entrypoint (bind to Railway's PORT)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
