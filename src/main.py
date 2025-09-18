# src/main.py
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

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
# expose db under current_app.extensions["sqlalchemy"].db (compat with earlier helpers)
app.extensions["sqlalchemy"].db = db  # type: ignore[attr-defined]

# ------------------------------------------------------------------------------
# Products table bootstrap
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
    ensure_products_table()
    print("[info] products table ready")

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
            clauses.append("(LOWER(name) LIKE :q OR LOWER(sku) LIKE :q OR LOWER(category) LIKE :q)")
            params["q"] = f"%{search.lower()}%"
        if category:
            clauses.append("LOWER(category) = :cat")
            params["cat"] = category.lower()

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = text(
            "SELECT id, name, sku, category, price, image_url, description "
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
# Optional seed
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
# Admin endpoints (inline; no blueprint import)
# ------------------------------------------------------------------------------
@app.get("/api/admin/ping")
def admin_ping():
    return jsonify(ok=True, where="admin"), 200

def _generate_description_stub(p: dict) -> str:
    parts = [
        p.get("name") or "Performance Part",
        p.get("category") or "",
        f"SKU {p.get('sku')}" if p.get("sku") else "",
    ]
    headline = " ".join(s for s in parts if s).strip()
    details = [
        "Engineered for responsive, reliable performance.",
        "Quality materials for daily use and spirited driving.",
        "Review fitment and specs for best results.",
    ]
    return f"{headline}. " + " ".join(details)

def _generate_description_ai(p: dict) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    try:
        from openai import OpenAI
    except Exception as e:
        raise RuntimeError(f"openai package not available: {e}")
    client = OpenAI(api_key=api_key)
    model       = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.environ.get("OPENAI_TEMPERATURE", "0.3"))
    max_tokens  = int(os.environ.get("OPENAI_MAX_TOKENS", "220"))
    name      = p.get("name") or ""
    category  = p.get("category") or ""
    sku       = p.get("sku") or ""
    price     = p.get("price") or ""
    image_url = p.get("image_url") or ""
    specs     = p.get("specs") or ""
    system = "You are a senior product copywriter for performance automotive parts."
    user = (
        "Write an 80–120 word product description. Tone: confident, technical, clear. "
        "Include 2–3 key benefits, one build/material detail, and a light fitment hint if relevant. "
        f"\n\nName: {name}\nCategory: {category}\nSKU: {sku}\nPrice: {price}\n"
        f"Image URL (optional): {image_url}\nSpecs/notes (optional): {specs}"
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user",  "content": user}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    text_out = (resp.choices[0].message.content or "").strip()
    if not text_out:
        raise RuntimeError("Empty AI response")
    return text_out

def _generate_description(p: dict) -> str:
    try:
        return _generate_description_ai(p)
    except Exception:
        return _generate_description_stub(p)

@app.route("/api/admin/ai/describe", methods=["GET", "POST"])
def ai_describe():
    try:
        if request.method == "POST":
            data = request.get_json(force=True) or {}
        else:
            data = {
                "name":     (request.args.get("name") or "").strip(),
                "sku":      (request.args.get("sku") or "").strip(),
                "category": (request.args.get("category") or "").strip(),
                "price":    (request.args.get("price") or "").strip(),
                "image_url":(request.args.get("image_url") or "").strip(),
                "specs":    (request.args.get("specs") or "").strip(),
            }
        desc = _generate_description(data)
        return jsonify({"description": desc}), 200
    except Exception as e:
        return jsonify(error="ServerError", message=str(e)), 500

def _insert_product_row(p: dict) -> int:
    ensure_products_table()
    ins = text("""
      INSERT INTO products (name, sku, category, price, image_url, description)
      VALUES (:name, :sku, :category, :price, :image_url, :description)
    """)
    db.session.execute(ins, {
        "name": (p.get("name") or "").strip(),
        "sku": (p.get("sku") or "").strip(),
        "category": (p.get("category") or "").strip(),
        "price": float(p.get("price") or 0),
        "image_url": (p.get("image_url") or "").strip(),
        "description": (p.get("description") or "").strip(),
    })
    db.session.commit()
    new_id = db.session.execute(text("SELECT last_insert_rowid()")).scalar_one()
    return int(new_id)

@app.post("/api/admin/products")
def admin_create_product():
    try:
        data = request.get_json(force=True) or {}
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify(error="ValidationError", message="name is required"), 400
        if not data.get("description"):
            data["description"] = _generate_description(data)
        new_id = _insert_product_row(data)
        return jsonify({"id": new_id}), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(error=type(e).__name__, message=str(e)), 500
    except Exception as e:
        return jsonify(error="ServerError", message=str(e)), 500

@app.post("/api/admin/products/upload")
def admin_upload_product():
    try:
        form = request.form
        name = (form.get("name") or "").strip()
        if not name:
            return jsonify(error="ValidationError", message="name is required"), 400

        image_url = (form.get("image_url") or "").strip()
        file = request.files.get("image")
        if file and file.filename:
            fn = secure_filename(file.filename)
            uploads = os.path.join(app.root_path, "static", "uploads")
            os.makedirs(uploads, exist_ok=True)
            path = os.path.join(uploads, fn)
            file.save(path)
            image_url = f"/static/uploads/{fn}"

        payload = {
            "name": name,
            "sku": (form.get("sku") or "").strip(),
            "category": (form.get("category") or "").strip(),
            "price": float(form.get("price") or 0),
            "image_url": image_url,
            "description": (form.get("description") or "").strip(),
            "specs": (form.get("specs") or "").strip(),
        }
        if not payload["description"]:
            payload["description"] = _generate_description(payload)

        new_id = _insert_product_row(payload)
        return jsonify({"id": new_id, "image_url": image_url}), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify(error=type(e).__name__, message=str(e)), 500
    except Exception as e:
        return jsonify(error="ServerError", message=str(e)), 500

# ------------------------------------------------------------------------------
# Debug: list all routes (remove later)
# ------------------------------------------------------------------------------
@app.get("/__routes")
def list_routes():
    out = []
    for rule in app.url_map.iter_rules():
        methods = ",".join(sorted(m for m in rule.methods if m not in {"HEAD","OPTIONS"}))
        out.append({"rule": str(rule), "methods": methods})
    return jsonify(out), 200

# ------------------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"[info] starting server on 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port)
