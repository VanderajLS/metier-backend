# src/main.py
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# ------------------------------------------------------------------------------
# App & CORS
# ------------------------------------------------------------------------------
app = Flask(__name__, static_folder="static", static_url_path="/")
CORS(app, resources={r"/api/*": {"origins": "*"}, r"/health": {"origins": "*"}})

# ------------------------------------------------------------------------------
# Database config (SQLite in /tmp by default; works on Railway)
# ------------------------------------------------------------------------------
DB_URL = (os.environ.get("DATABASE_URL") or "").strip()
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)
if not DB_URL:
    DB_URL = "sqlite:////tmp/metier.db"

app.config["SQLALCHEMY_DATABASE_URI"] = DB_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Compatibility alias so blueprints can access `current_app.extensions["sqlalchemy"].db`
# (Flask-SQLAlchemy stores the extension under 'sqlalchemy'; we attach `.db` to it.)
app.extensions["sqlalchemy"].db = db  # type: ignore[attr-defined]

# ------------------------------------------------------------------------------
# Bootstrap products table (simple schema for MVP)
# ------------------------------------------------------------------------------
CREATE_PRODUCTS_SQL = """
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  sku TEXT,
  category TEXT,
  price REAL DEFAULT 0,
  image_url TEXT,
  description TEXT
);
"""

def ensure_products_table():
    db.session.execute(text(CREATE_PRODUCTS_SQL))
    db.session.commit()

with app.app_context():
    try:
        ensure_products_table()
        print("[info] products table ready")
    except Exception as e:
        print(f"[warn] ensure_products_table failed: {e}")

# ------------------------------------------------------------------------------
# Auto-register blueprints (e.g., routes/admin.py exposes `admin_bp`)
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

_maybe_register("admin", "admin_bp")

# ------------------------------------------------------------------------------
# Health & Root
# ------------------------------------------------------------------------------
@app.get("/health")
def health():
    return jsonify(ok=True), 200

@app.get("/")
def root():
    return jsonify(status="ok", service="metier-backend"), 200

# ------------------------------------------------------------------------------
# Products list (supports ?search=, ?category=, ?limit=)
# ------------------------------------------------------------------------------
@app.get("/api/products")
def api_products():
    try:
        search = (request.args.get("search") or "").strip()
        category = (request.args.get("category") or "").strip()
        limit = int(request.args.get("limit") or 50)

        clauses, params = [], {}
        if search:
            clauses.append(
                "(LOWER(name) LIKE :q OR LOWER(sku) LIKE :q OR LOWER(category) LIKE :q)"
            )
            params["q"] = f"%{search.lower()}%"
        if category:
            clauses.append("LOWER(category) = :cat")
            params["cat"] = category.lower()

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = text(
            f"SELECT id, name, sku, category, price, image_url, description "
            f"FROM products {where_sql} ORDER BY id DESC LIMIT :lim"
        )
        params["lim"] = limit

        rows = db.session.execute(sql, params).mappings().all()
        return jsonify([dict(r) for r in rows]), 200
    except SQLAlchemyError as e:
        return jsonify(error=type(e).__name__, message=str(e)), 500
    except Exception as e:
        return jsonify(error="ServerError", message=str(e)), 500

# ------------------------------------------------------------------------------
# Optional seed endpoint (adds a couple demo items)
# ------------------------------------------------------------------------------
@app.post("/api/seed")
def api_seed():
    try:
        ensure_products_table()
        count = db.session.execute(text("SELECT COUNT(*) AS c FROM products")).scalar_one()
        if count and count > 0:
            return jsonify(message="Already seeded", count=int(count)), 200

        sample = [
            {
                "name": "GTX 2867R Turbocharger",
                "sku": "MET-7811",
                "category": "Turbochargers",
                "price": 1299.00,
                "image_url": "https://images.unsplash.com/photo-1542365887-6dd6fc8f9f0e?q=80&w=1600&auto=format&fit=crop",
                "description": "Dual ball-bearing turbo for responsive street builds."
            },
            {
                "name": "Front-Mount Intercooler Kit",
                "sku": "MET-FMIC-900",
                "category": "Intercoolers",
                "price": 899.00,
                "image_url": "https://images.unsplash.com/photo-1587440871875-191322ee64b0?q=80&w=1600&auto=format&fit=crop",
                "description": "High-efficiency core with mandrel-bent piping."
            }
        ]

        ins = text("""
            INSERT INTO products (name, sku, category, price, image_url, description)
            VALUES (:name, :sku, :category, :price, :image_url, :description)
        """)
        for p in sample:
            db.session.execute(ins, p)
        db.session.commit()

        return jsonify(message="Seeded", inserted=len(sample)), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(error=type(e).__name__, message=str(e)), 500
    except Exception as e:
        return jsonify(error="ServerError", message=str(e)), 500

# ------------------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
