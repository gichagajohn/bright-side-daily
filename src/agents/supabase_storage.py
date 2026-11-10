"""
Supabase Storage uploader — Bright Side Daily

Instagram's Graph API cannot accept a local file upload. It needs a
public HTTPS image URL. This module pushes the generated image to a
public Supabase Storage bucket and returns the public URL.

Required environment variables:
    SUPABASE_URL          https://<project-ref>.supabase.co
    SUPABASE_SERVICE_KEY  service_role key (server side only)
    SUPABASE_BUCKET       bucket name, default: social-images
"""

import logging
import mimetypes
import os
import uuid
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("supabase_storage")


class SupabaseStorage:
    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        self.key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        self.bucket = os.environ.get("SUPABASE_BUCKET", "social-images")

        if not self.url or not self.key:
            raise EnvironmentError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set "
                "to publish images to Instagram."
            )

    # ── Upload ────────────────────────────────────────────────────────────────

    def upload(self, image_path, folder="bright-side"):
        """Upload an image and return its public URL."""

        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        extension = path.suffix.lower() or ".jpg"
        object_name = f"{folder}/{uuid.uuid4().hex}{extension}"

        content_type = (
            mimetypes.guess_type(path.name)[0] or "image/jpeg"
        )

        endpoint = (
            f"{self.url}/storage/v1/object/"
            f"{self.bucket}/{object_name}"
        )

        with open(path, "rb") as file:
            response = requests.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {self.key}",
                    "apikey": self.key,
                    "Content-Type": content_type,
                    "x-upsert": "true",
                    "cache-control": "3600",
                },
                data=file,
                timeout=120,
            )

        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"Supabase upload failed "
                f"({response.status_code}): {response.text[:300]}"
            )

        public_url = (
            f"{self.url}/storage/v1/object/public/"
            f"{self.bucket}/{object_name}"
        )

        log.info("Uploaded to Supabase: %s", public_url)
        return public_url

    # ── Housekeeping ──────────────────────────────────────────────────────────

    def delete(self, public_url):
        """Remove an uploaded object. Safe to call in a finally block."""

        marker = f"/object/public/{self.bucket}/"

        if marker not in public_url:
            return

        object_name = public_url.split(marker, 1)[1]
        endpoint = (
            f"{self.url}/storage/v1/object/"
            f"{self.bucket}/{object_name}"
        )

        try:
            requests.delete(
                endpoint,
                headers={
                    "Authorization": f"Bearer {self.key}",
                    "apikey": self.key,
                },
                timeout=30,
            )
        except Exception as exc:
            log.warning("Could not delete remote image: %s", exc)
