import os
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# Initialize Flask
app = Flask(__name__)
CORS(app)

# -------------------------------
# Database config (Postgres + SQLite fallback)
# -------------------------------
if os.environ.get("DATABASE_URL"):
    # Railway often uses postgres://, SQLAlchemy with psycopg v3 expects postgresql+psycopg://
    db_url = os.environ["DATABASE_URL"].replace("postgres://", "postgresql+psycopg://")
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
else:
    # Local fallback
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///metier_cx.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# -------------------------------
# Blueprints
# -------------------------------
from src.routes.admin import admin_bp
app.register_blueprint(admin_bp)

# -------------------------------
# Health check
# -------------------------------
@app.route("/health")
def health():
    return jsonify(ok=True)

# -------------------------------
# Run
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
