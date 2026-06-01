"""
Google Gemini API client for text and image generation.

Requires: requests

Authentication:
    GEMINI_API_KEY: API key from https://aistudio.google.com/apikey
"""

import base64
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

import requests

from ...config import require_secret


class GeminiClient:
    """
    Google Gemini API client.

    Features:
    - Chat completions (text)
    - Image generation (Gemini 3 Pro Image)
    - Style reference support for image generation
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key: str = None, model: str = "gemini-3-pro-image-preview"):
        self.api_key = api_key or require_secret("GEMINI_API_KEY")
        self.model = model

    def _url(self, model: str, method: str) -> str:
        return f"{self.BASE_URL}/models/{model}:{method}?key={self.api_key}"

    # --- Text generation ---

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        model: str = None,
    ) -> Dict[str, Any]:
        """
        Send a chat completion request.

        Args:
            messages: List of dicts with 'role' ('user'/'model') and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            model: Override default model

        Returns:
            Full API response dict
        """
        contents = []
        system_instruction = None

        for msg in messages:
            role = msg["role"]
            if role == "system":
                system_instruction = msg["content"]
                continue
            # Map 'assistant' to 'model' for Gemini API
            if role == "assistant":
                role = "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        resp = requests.post(
            self._url(model or self.model, "generateContent"),
            json=payload,
            timeout=60,
        )
        if not resp.ok:
            raise Exception(f"Gemini API error: {resp.status_code} {resp.text}")

        return resp.json()

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        model: str = None,
    ) -> str:
        """Simple completion with system and user prompts. Returns text."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        result = self.chat(messages, temperature=temperature, max_tokens=max_tokens, model=model)
        return result["candidates"][0]["content"]["parts"][0]["text"]

    # --- Image generation ---

    def generate_image(
        self,
        prompt: str,
        style_guidelines: str = None,
        reference_image_path: str = None,
        output_dir: str = None,
        model: str = "gemini-3-pro-image-preview",
    ) -> Dict[str, Any]:
        """
        Generate an image using Gemini.

        Args:
            prompt: Text description of the image
            style_guidelines: Optional style directions (colors, mood, etc.)
            reference_image_path: Optional local image file for style transfer
            output_dir: Directory to save the image (default: current dir)
            model: Model to use for image generation

        Returns:
            Dict with status, image_path, filename
        """
        full_prompt = prompt
        if style_guidelines:
            full_prompt += f"\n\nStyle guidelines: {style_guidelines}"

        parts = []

        # Add reference image if provided
        if reference_image_path:
            path = Path(reference_image_path)
            if not path.exists():
                return {"status": "error", "error": f"Reference image not found: {reference_image_path}"}
            import mimetypes
            mime_type = mimetypes.guess_type(str(path))[0] or "image/png"
            image_b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
            parts.append({"inline_data": {"mime_type": mime_type, "data": image_b64}})
            full_prompt = f"Generate a NEW image in the exact same visual style as this reference image. Match the colors, patterns, textures and artistic style closely.\n\n{full_prompt}"

        parts.append({"text": full_prompt})

        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": 0.6,
                "responseModalities": ["image", "text"],
            },
        }

        resp = requests.post(self._url(model, "generateContent"), json=payload, timeout=120)
        if not resp.ok:
            return {"status": "error", "error": f"Gemini API error: {resp.status_code} {resp.text}"}

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return {"status": "error", "error": "No candidates in response"}

        # Find image part in response
        for part in candidates[0].get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline:
                image_bytes = base64.b64decode(inline["data"])
                mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                ext = "png" if "png" in mime else "jpg"

                out = Path(output_dir) if output_dir else Path.cwd()
                out.mkdir(parents=True, exist_ok=True)

                sanitized = re.sub(r'[^\w\s-]', '', prompt).replace(' ', '_')[:50].strip('_').lower()
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{sanitized}.{ext}"
                file_path = out / filename
                file_path.write_bytes(image_bytes)

                return {
                    "status": "success",
                    "image_path": str(file_path.absolute()),
                    "filename": filename,
                    "mime_type": mime,
                }

        return {"status": "error", "error": "No image data in response"}

    def edit_image(
        self,
        prompt: str,
        image_b64: str,
        image_mime: str = "image/jpeg",
        model: str = "gemini-3-pro-image-preview",
        reference_images: List[Dict[str, str]] | None = None,
        image_size: str | None = None,
    ) -> Dict[str, Any]:
        """
        Edit/transform an image using Gemini (base64 in/out).

        Args:
            prompt: Instructions for the transformation
            image_b64: Base64-encoded input image (no data: prefix)
            image_mime: MIME type of the input image
            model: Model to use
            reference_images: Optional list of {"data": b64, "mime_type": str} dicts
                inserted before the subject image as style references
            image_size: Optional output size — e.g. "1024x1024", "2048x2048"

        Returns:
            Dict with status, data (base64), mime_type — or status, error
        """
        parts = [{"text": prompt}]
        if reference_images:
            for ref in reference_images:
                parts.append({"inline_data": {"mime_type": ref["mime_type"], "data": ref["data"]}})
        parts.append({"inline_data": {"mime_type": image_mime, "data": image_b64}})

        gen_config = {
            "responseModalities": ["IMAGE", "TEXT"],
        }
        if image_size:
            gen_config["imageConfig"] = {"imageSize": image_size}

        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": gen_config,
        }

        resp = requests.post(self._url(model, "generateContent"), json=payload, timeout=120)
        if not resp.ok:
            return {"status": "error", "error": f"Gemini API error: {resp.status_code} {resp.text[:200]}"}

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return {"status": "error", "error": "No candidates (content may have been filtered)"}

        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts = []
        for part in parts:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline:
                return {
                    "status": "success",
                    "data": inline["data"],
                    "mime_type": inline.get("mimeType") or inline.get("mime_type") or "image/png",
                }
            if part.get("text"):
                text_parts.append(part["text"])

        reason = candidates[0].get("finishReason", "")
        detail = "; ".join(text_parts) if text_parts else ""
        msg = f"No image in response (finishReason={reason})"
        if detail:
            msg += f": {detail[:300]}"
        return {"status": "error", "error": msg}
