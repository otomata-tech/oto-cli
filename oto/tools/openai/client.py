"""
OpenAI image generation client (gpt-image).

Requires: requests

Authentication:
    OPENAI_API_KEY: API key from https://platform.openai.com/api-keys
"""

import base64
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

import requests

from ...config import require_secret


class OpenAIImageClient:
    """
    OpenAI image client.

    Features:
    - Text-to-image (gpt-image-2) via /v1/images/generations
    - Image editing / compositing via /v1/images/edits (subject + reference images)

    gpt-image models always return base64 (b64_json), never a URL.
    """

    BASE_URL = "https://api.openai.com/v1"

    def __init__(self, api_key: str = None, model: str = "gpt-image-2"):
        self.api_key = api_key or require_secret("OPENAI_API_KEY")
        self.model = model

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    @staticmethod
    def _mime_to_ext(mime: str) -> str:
        if "png" in mime:
            return "png"
        if "webp" in mime:
            return "webp"
        return "jpg"

    # --- Text-to-image ---

    def generate_image(
        self,
        prompt: str,
        output_dir: str = None,
        model: str = None,
        size: str = "1024x1024",
    ) -> Dict[str, Any]:
        """
        Generate an image from a text prompt.

        Args:
            prompt: Text description of the image
            output_dir: Directory to save the image (default: current dir)
            model: Override default model
            size: Output size — "1024x1024", "1536x1024", "1024x1536", or "auto"

        Returns:
            Dict with status, image_path, filename — or status, error
        """
        payload = {
            "model": model or self.model,
            "prompt": prompt,
            "n": 1,
        }
        if size:
            payload["size"] = size

        resp = requests.post(
            f"{self.BASE_URL}/images/generations",
            headers=self._headers(),
            json=payload,
            timeout=180,
        )
        if not resp.ok:
            return {"status": "error", "error": f"OpenAI API error: {resp.status_code} {resp.text[:300]}"}

        data = resp.json()
        items = data.get("data", [])
        b64 = items[0].get("b64_json") if items else None
        if not b64:
            return {"status": "error", "error": "No image data in OpenAI response"}

        image_bytes = base64.b64decode(b64)
        out = Path(output_dir) if output_dir else Path.cwd()
        out.mkdir(parents=True, exist_ok=True)

        sanitized = re.sub(r"[^\w\s-]", "", prompt).replace(" ", "_")[:50].strip("_").lower()
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{sanitized}.png"
        file_path = out / filename
        file_path.write_bytes(image_bytes)

        return {
            "status": "success",
            "image_path": str(file_path.absolute()),
            "filename": filename,
            "mime_type": "image/png",
        }

    # --- Image editing / compositing ---

    def edit_image(
        self,
        prompt: str,
        image_b64: str,
        image_mime: str = "image/jpeg",
        model: str = None,
        reference_images: List[Dict[str, str]] | None = None,
        image_size: str | None = None,
    ) -> Dict[str, Any]:
        """
        Edit/transform an image (base64 in, base64 out).

        Args:
            prompt: Instructions for the transformation
            image_b64: Base64-encoded subject image (no data: prefix)
            image_mime: MIME type of the subject image
            model: Override default model
            reference_images: Optional list of {"data": b64, "mime_type": str} dicts,
                sent before the subject image as style/context references
            image_size: Optional output size (e.g. "1024x1024", "auto")

        Returns:
            Dict with status, data (base64), mime_type — or status, error
        """
        # OpenAI /v1/images/edits takes repeated `image` fields (multipart).
        # Order: references first, subject last — aligned with the Gemini client.
        files = []
        if reference_images:
            for i, ref in enumerate(reference_images):
                ext = self._mime_to_ext(ref["mime_type"])
                files.append(
                    ("image[]", (f"ref_{i}.{ext}", base64.b64decode(ref["data"]), ref["mime_type"]))
                )
        subject_ext = self._mime_to_ext(image_mime)
        files.append(("image[]", (f"subject.{subject_ext}", base64.b64decode(image_b64), image_mime)))

        data = {"model": model or self.model, "prompt": prompt, "n": "1"}
        if image_size:
            data["size"] = image_size

        resp = requests.post(
            f"{self.BASE_URL}/images/edits",
            headers=self._headers(),
            data=data,
            files=files,
            timeout=180,
        )
        if not resp.ok:
            return {"status": "error", "error": f"OpenAI API error: {resp.status_code} {resp.text[:300]}"}

        body = resp.json()
        items = body.get("data", [])
        b64 = items[0].get("b64_json") if items else None
        if not b64:
            return {"status": "error", "error": "No image data in OpenAI response"}

        return {"status": "success", "data": b64, "mime_type": "image/png"}
