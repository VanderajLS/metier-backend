from __future__ import annotations
import os
from typing import Dict, Any
from flask import Blueprint, jsonify, request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import boto3
from botocore.config import Config
from datetime import datetime
from urllib.parse import urlparse
import traceback

# Import db from main.py
from src.main import db
from openai import OpenAI

# ------------------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------------------
admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

client = OpenAI()

# ------------------------------------------------------------------------------
# R2 helpers
# ------------------------------------------------------------------------------
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME") or os.getenv("R2_BUCKET")
R2_ENDPOINT = os.getenv("R2_ENDPOINT", "").rstrip("/")
R2_PUBLIC_BASE = os.getenv("R2_PUBLIC_BASE", "").rstrip("/")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")

s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4")  # Force SigV4
)

def _normalize_public_base(base: str, key: str) -> str:
    if not base:
        return None
    parsed = urlparse(base)
    clean_path = parsed.path.strip("/")
    if clean_path == R2_BUCKET_NAME:
        clean_path = ""
    root = f"{parsed.scheme}://{parsed.netloc}"
    if clean_path:
        root = f"{root}/{clean_path}"
    return f"{root}/{key}"

# ------------------------------------------------------------------------------
# DB helpers
# ------------------------------------------------------------------------------
def _ensure_products_table():
    try:
        sql = """
        CREATE TABLE IF NOT EXISTS products (
          id SERIAL PRIMARY KEY,
          name TEXT,
          sku TEXT,
          category TEXT,
          price REAL DEFAULT 0,
          inventory INT DEFAULT 0,
          image_url TEXT,
          description TEXT,
          product_images TEXT
        );
        """
        db.session.execute(text(sql))
        db.session.commit()
    except Exception as e:
        print("DB ERROR in _ensure_products_table:", str(e))
        traceback.print_exc()
        raise

def _insert_product(p: Dict[str, Any]) -> int:
    _ensure_products_table()
    ins = text("""
      INSERT INTO products (name, sku, category, price, inventory, image_url, description, product_images)
      VALUES (:name, :sku, :category, :price, :inventory, :image_url, :description, :product_images)
    """)
    db.session.execute(ins, {
        "name": (p.get("name") or "").strip(),
        "sku": (p.get("sku") or "").strip(),
        "category": (p.get("category") or "").strip(),
        "price": float(p.get("price") or 0),
        "inventory": int(p.get("inventory") or 0),
        "image_url": (p.get("image_url") or "").strip(),
        "description": (p.get("description") or "").strip(),
        # store list of product_images as comma-separated string
        "product_images": ",".join(p.get("product_images", []))
    })
    db.session.commit()
    row_id = db.session.execute(text("SELECT lastval()")).scalar_one()
    return int(row_id)

# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------
@admin_bp.route("/ping")
def ping():
    return jsonify(ok=True, where="admin")

# --- Image Presign ---
@admin_bp.post("/images/presign")
def presign_image():
    """Generate a presigned PUT URL for uploading directly to R2."""
    try:
        data = request.get_json(force=True) or {}
        file_name = data.get("fileName")
        content_type = data.get("contentType", "application/octet-stream")
        folder = data.get("folder", "").strip()
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        key = f"{folder}/{timestamp}_{file_name}" if folder else f"{timestamp}_{file_name}"

        presigned_url = s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": R2_BUCKET_NAME, "Key": key, "ContentType": content_type},
            ExpiresIn=3600,
        )

        public_url = _normalize_public_base(R2_PUBLIC_BASE, key)

        return jsonify({
            "upload_url": presigned_url,
            "public_url": public_url,
            "key": key
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify(error="ServerError", message=str(e)), 500

# --- Create Product ---
@admin_bp.post("/products")
def create_product():
    """Create product from JSON."""
    try:
        data = request.get_json(force=True) or {}
        new_id = _insert_product(data)
        return jsonify({"id": new_id}), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify(error=type(e).__name__, message=str(e)), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify(error="ServerError", message=str(e)), 500

# --- List Products (admin) ---
@admin_bp.get("/products")
def list_products_admin():
    try:
        _ensure_products_table()
        rows = db.session.execute(
            text("SELECT * FROM products ORDER BY id DESC")
        ).mappings().all()
        # expand product_images string into list
        results = []
        for r in rows:
            item = dict(r)
            if item.get("product_images"):
                item["product_images"] = item["product_images"].split(",")
            else:
                item["product_images"] = []
            results.append(item)
        return jsonify(results)
    except Exception as e:
        traceback.print_exc()
        return jsonify(error="ServerError", message=str(e)), 500

# --- Public Catalog ---
@admin_bp.get("/public")
def list_products_public():
    try:
        _ensure_products_table()
        rows = db.session.execute(
            text("SELECT * FROM products ORDER BY id DESC")
        ).mappings().all()
        results = []
        for r in rows:
            item = dict(r)
            if item.get("product_images"):
                item["product_images"] = item["product_images"].split(",")
            else:
                item["product_images"] = []
            results.append(item)
        return jsonify(results)
    except Exception as e:
        traceback.print_exc()
        return jsonify(error="ServerError", message=str(e)), 500

# --- AI Description ---
@admin_bp.post("/ai/describe")
def ai_describe():
    """Use OpenAI Vision to extract product info and generate description."""
    try:
        data = request.get_json(force=True) or {}
        image_url = data.get("image_url")
        price = data.get("price", "")
        inventory = data.get("inventory", "")

        if not image_url:
            return jsonify(error="ValidationError", message="image_url is required"), 400

        prompt = (
            "You are analyzing a product description image. "
            "Extract the following if available: product name, category, SKU, and specifications. "
            "Then write a short, professional marketing description suitable for an e-commerce site."
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            max_tokens=500,
            temperature=0.7,
        )

        description = response.choices[0].message.content.strip()

        return jsonify({
            "name": None,        # leave blank for now (editable later)
            "category": None,
            "sku": None,
            "specs": None,
            "description": description,
            "price": price,
            "inventory": inventory
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify(error="ServerError", message=str(e)), 500
