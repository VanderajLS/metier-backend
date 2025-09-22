# src/main.py
import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from src.routes.admin import admin_bp
import boto3

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

# Database setup
db_path = os.getenv("DATABASE_URL", "sqlite:///metier_cx.db")
app.config["SQLALCHEMY_DATABASE_URI"] = db_path
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB upload limit
db = SQLAlchemy(app)

# Register admin routes
app.register_blueprint(admin_bp)

# Healthcheck
@app.route("/health")
def health():
    return jsonify(ok=True)

# Serve frontend (if static build exists)
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

# Show all active routes (for debugging)
@app.route("/__routes")
def list_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({"rule": str(rule), "methods": ",".join(rule.methods)})
    return jsonify(routes)

# ---------- New: Presigned Upload Endpoint for R2 ----------
@app.route("/api/admin/images/presign", methods=["POST"])
def presign_image_upload():
    from flask import request

    try:
        # Read input
        body = request.get_json(force=True)
        file_name = body.get("fileName")
        content_type = body.get("contentType", "application/octet-stream")
        folder = body.get("folder", "").strip("/")

        if not file_name:
            return jsonify(error="Missing fileName"), 400

        key = f"{folder}/{file_name}" if folder else file_name

        r2 = boto3.client(
            "s3",
            endpoint_url=os.environ["R2_ENDPOINT"],
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        )

        bucket = os.environ["R2_BUCKET"]
        pub_base = os.environ.get("R2_PUBLIC_BASE", "").rstrip("/")

        presigned = r2.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=3600,
        )

        return jsonify({
            "upload_url": presigned,
            "public_url": f"{pub_base}/{key}" if pub_base else None,
            "key": key,
        })

    except Exception as e:
        return jsonify(error="ServerError", message=str(e)), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
