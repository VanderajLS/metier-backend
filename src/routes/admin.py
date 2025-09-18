# src/routes/admin.py
from __future__ import annotations
import os
from typing import Dict, Any
from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

admin_bp = Blueprint("admin", url_prefix="/api/admin")

# ---------- DB helpers ----------
def _ensure_products_table():
    sql = """
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
    db = current_app.extensions["sqlalchemy"].db
    db.session.execute(text(sql))
    db.session.commit()

def _insert_product(p: Dict[str, Any]) -> int:
    _ensure_products_table()
    ins = text("""
      INSERT INTO products (name, sku, category, price, image_url, description)
      VALUES (:name, :sku, :category, :price, :image_url, :description)
    """)
    db = current_app.extensions["sqlalchemy"].db
    db.session.execute(ins, {
        "name": p.get("name", "").strip(),
        "sku": (p.get("sku") or "").strip(),
        "category": (p.get("category") or "").strip(),
        "price": float(p.get("price") or 0),
        "image_url": (p.get("image_url") or "").strip(),
        "description": (p.get("description") or "").strip(),
    })
    db.session.commit()
    row_id = db.session.execute(text("SELECT last_insert_rowid()")).scalar_one()
    return int(row_id)

# ---------- AI description (stub → OpenAI if key present) ----------
def _generate_description_stub(p: Dict[str, Any]) -> str:
    parts = [
        p.get("name") or "Performance Part",
        p.get("category") or "",
        f"SKU {p.get('sku')}" if p.get("sku") else "",
    ]
    headline = " ".join(s for s in parts if s).strip()
    details = [
        "Engineered for responsive, reliable performance.",
        "Quality materials for daily use and spirited driving.",
        "Review fitment and specs for best results."
    ]
    return f"{headline}. " + " ".join(details)

def _generate_description_ai(p: Dict[str, Any]) -> str:
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

def _generate_description(p: Dict[str, Any]) -> str:
    try:
        return _generate_description_ai(p)
    except Exception:
        return _generate_description_stub(p)

# ---------- Routes ----------
@admin_bp.post("/ai/describe")
def ai_describe():
    """Return product copy. Uses OpenAI if configured; otherwise the local stub."""
    try:
        data = request.get_json(force=True) or {}
        desc = _generate_description(data)
        return jsonify({"description": desc}), 200
    except Exception as e:
        return jsonify(error="ServerError", message=str(e)), 500

@admin_bp.post("/products")
def create_product():
    """Create product from JSON; auto-generate description when omitted."""
    try:
        data = request.get_json(force=True) or {}
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify(error="ValidationError", message="name is required"), 400
        if not data.get("description"):
            data["description"] = _generate_description(data)
        new_id = _insert_product(data)
        return jsonify({"id": new_id}), 201
    except SQLAlchemyError as e:
        current_app.extensions["sqlalchemy"].db.session.rollback()
        return jsonify(error=type(e).__name__, message=str(e)), 500
    except Exception as e:
        return jsonify(error="ServerError", message=str(e)), 500

@admin_bp.post("/products/upload")
def upload_product_with_image():
    """
    Multipart form:
      - name (required)
      - sku, category, price, description, specs (optional)
      - image (file) → saved to /static/uploads; image_url becomes /static/uploads/<file>
    """
    try:
        form = request.form
        name = (form.get("name") or "").strip()
        if not name:
            return jsonify(error="ValidationError", message="name is required"), 400

        image_url = (form.get("image_url") or "").strip()
        file = request.files.get("image")
        if file and file.filename:
            fn = secure_filename(file.filename)
            uploads = os.path.join(current_app.root_path, "static", "uploads")
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

        new_id = _insert_product(payload)
        return jsonify({"id": new_id, "image_url": image_url}), 201
    except SQLAlchemyError as e:
        current_app.extensions["sqlalchemy"].db.session.rollback()
        return jsonify(error=type(e).__name__, message=str(e)), 500
    except Exception as e:
        return jsonify(error="ServerError", message=str(e)), 500
