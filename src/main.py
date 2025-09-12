# src/main.py
import os

from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# ------------------------------------------------------------------------------
# App + Config
# ------------------------------------------------------------------------------
app = Flask(__name__, static_folder="static", static_url_path="/")

# CORS: allow all for now (tighten later to your Vercel domain if you want)
CORS(app, resources={r"/api/*": {"origins": "*"}, r"/health": {"origins": "*"}})

# Database config:
# Prefer DATABASE_URL (e.g., Railway Postgres). Fallback to writable SQLite in /tmp.
DB_URL = os.environ.get("DATABASE_URL", "").strip()
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)
if not DB_URL:
    # Always writable in container
    DB_URL = "sqlite:////tmp/metier.db"

app.config["SQLALCHEMY_DATABASE_URI"] = DB_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ------------------------------------------------------------------------------
# Models import (so metadata is known before create_all)
# NOTE: These imports are inside try blocks to avoid hard crashes
# if a module name or symbol differs. Adjust names if your blueprints differ.
# ------------------------------------------------------------------------------
try:
    # If your models reference `db` from main.py, importing after `db` is defined is important.
    from models.product import Product  # noqa: F401
    from models.order import Order      # noqa: F401
    from models.user import User        # noqa: F401
except Exception as e:
    # Log to console; app will still start so you can see the error in logs
    print(f"[warn] Could not import models: {e}")

# Create tables safely
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"[warn] db.create_all() failed: {e}")

# ------------------------------------------------------------------------------
# Blueprint registration (register only if present)
# Expecting product_bp, cart_bp, order_bp, user_bp, admin_bp in routes/*
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
        print(f"[warn] Could not register blueprint {module_name}.{bp_name}: {e}")

# Try common blueprint names; adjust if yours are different
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
# Entrypoint
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # Listen on all interfaces so Railway can reach it
    app.run(host="0.0.0.0", port=port)
