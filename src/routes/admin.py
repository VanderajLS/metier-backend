from flask import Blueprint, request, jsonify
import os
import boto3
from datetime import datetime

from src.models.product import Product, db

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

# R2 config
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_ENDPOINT = os.getenv("R2_ENDPOINT")
R2_PUBLIC_BASE = os.getenv("R2_PUBLIC_BASE")  # e.g. https://pub-xxx.r2.dev

# boto3 R2 client
r2_client = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
)


@admin_bp.route("/images/presign", methods=["POST"])
def generate_presigned_post():
    """
    Generates a presigned URL for direct image upload to R2.
    Expects: JSON { fileName, contentType, folder }
    Returns: { url, fields, public_url }
    """
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
