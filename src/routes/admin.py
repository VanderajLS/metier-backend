from flask import Blueprint, request, jsonify, current_app
import os
import boto3
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

# ---------- R2 Presigned Upload ----------
@admin_bp.route("/images/presign", methods=["POST"])
def generate_presigned_post():
    try:
        data = request.get_json(force=True)
        file_name = data["fileName"]
        content_type = data["contentType"]
        folder = data.get("folder", "uploads")

        # Generate object key (path)
        key = f"{folder}/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file_name}"

        # Use R2 config from env
        r2 = boto3.client(
            "s3",
            endpoint_url=os.environ["R2_ENDPOINT"],
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        )

        presigned_post = r2.generate_presigned_post(
            Bucket=os.environ["R2_BUCKET_NAME"],
            Key=key,
            Fields={"Content-Type": content_type},
            Conditions=[{"Content-Type": content_type}],
            ExpiresIn=3600,
        )

        return jsonify({
            "url": presigned_post["url"],
            "fields": presigned_post["fields"],
            "public_url": f"{os.environ['R2_PUBLIC_BASE'].rstrip('/')}/{key}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------- Dummy Admin Ping ----------
@admin_bp.route("/ping")
def ping():
    return jsonify(ok=True, where="admin")

import boto3
from datetime import datetime

# Ensure these env vars are set in Railway
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_ENDPOINT = os.getenv("R2_ENDPOINT")
R2_PUBLIC_BASE = os.getenv("R2_PUBLIC_BASE")

r2_client = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
)

@admin_bp.route("/images/presign", methods=["POST"])
def generate_presigned_post():
    try:
        data = request.get_json()
        file_name = data["fileName"]
        content_type = data["contentType"]
        folder = data.get("folder", "uploads")

        key = f"{folder}/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file_name}"

        presigned_post = r2_client.generate_presigned_post(
            Bucket=R2_BUCKET_NAME,
            Key=key,
            Fields={"Content-Type": content_type},
            Conditions=[{"Content-Type": content_type}],
            ExpiresIn=3600,
        )

        return jsonify({
            "url": presigned_post["url"],
            "fields": presigned_post["fields"],
            "public_url": f"{R2_PUBLIC_BASE}/{key}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
