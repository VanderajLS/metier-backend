# src/main.py
import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from src.routes.admin import admin_bp  # your admin blueprint
import boto3

# ------------------------------------------------------------------------------
# App setup
# ------------------------------------------------------------------------------
app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

# ------------------------------------------------------------------------------
# Database setup
# ------------------------------------------------------------------------------
db_path = os.getenv("DATABASE_URL", "sqlite:///metier_cx.db")
app.config["SQLALCHEMY_DATABASE_URI"] = db_path
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload limit

db = SQLAlchemy(app)

# ------------------------------------------------------------------------------
# Register blueprints
# ------------------------------------------------------------------------------
app.register_blueprint(admin_bp)

# ------------------------------------------------------------------------------
# Healthcheck
# ------------------------------------------------------------------------------
@app.route("/health")
def health():
    return jsonify(ok=True)

# ------------------------------------------------------------------------------
# Serve frontend (static build if present)
# ------------------------------------------------------------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        index_path = os.path.join(app.static_folder, "index.html")
        if os.path.exists(index_path):
            return send_from_directory(app.static_folder, "index.html")
        return "Frontend not built", 404

# ------------------------------------------------------------------------------
# Debug route listing
# ------------------------------------------------------------------------------
@app.route("/__routes")
def list_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({"rule": str(rule), "methods": ",".join(rule.methods)})
    return jsonify(routes)
