#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Byteplus / Volcengine Ark — Seadance 2 + Seedream image generation
API key format: ark-xxxxxxxxxxxx
"""

import os
import time
import requests
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────

BYTEPLUS_API_KEY  = os.getenv("BYTEPLUS_API_KEY") or os.getenv("ARK_API_KEY")
BYTEPLUS_BASE_URL = os.getenv(
    "BYTEPLUS_BASE_URL",
    "https://ark.ap-southeast.bytepluses.com/api/v3"
)

# Model IDs — BytePlus international names (GET /models lists them; each must
# be activated in the Ark console before use)
# Image (text-to-image): Seedream 5.0
IMAGE_MODEL = os.getenv("BYTEPLUS_IMAGE_MODEL", "seedream-5-0-260128")

# Video: Dreamina Seedance 2.0 handles both image-to-video and text-to-video
VIDEO_MODEL_I2V = os.getenv("BYTEPLUS_VIDEO_MODEL_I2V", "dreamina-seedance-2-0-260128")
VIDEO_MODEL_T2V = os.getenv("BYTEPLUS_VIDEO_MODEL_T2V", "dreamina-seedance-2-0-260128")

# Seedream 5 rejects images under 3,686,400 px (~1920x1920); smaller sizes are
# scaled up keeping their aspect ratio. Set 0 for older models.
MIN_PIXELS = int(os.getenv("JIMENG_MIN_PIXELS", "3686400"))

AVAILABLE = bool(BYTEPLUS_API_KEY)


def fit_size(size: str) -> str:
    """'1792x1024' -> a WxH string meeting MIN_PIXELS, same aspect ratio."""
    try:
        w, h = (int(v) for v in size.lower().replace("*", "x").split("x"))
    except ValueError:
        return size
    if MIN_PIXELS and w * h < MIN_PIXELS:
        scale = (MIN_PIXELS / (w * h)) ** 0.5
        w, h = (-(-int(v * scale) // 16) * 16 for v in (w, h))  # round up to /16
    return f"{w}x{h}"


# ── Prompt builder ────────────────────────────────────────────

def build_cinematic_prompt(scene_data: dict) -> tuple[str, str]:
    """
    Returns (positive_prompt, negative_prompt) in photorealistic film style.
    scene_data keys: heading, location, time_of_day, mood, keywords, action
    """
    heading   = scene_data.get("heading", "")
    location  = scene_data.get("location", "")
    time_of_day = scene_data.get("time_of_day", "")
    mood      = scene_data.get("mood", "")
    keywords  = ", ".join(scene_data.get("keywords") or [])
    action    = (scene_data.get("action") or "")[:200]

    positive = (
        "cinematic film still, ultra realistic, 35mm photography, "
        "natural textures, real materials, weathered surfaces, "
        "film grain, shallow depth of field, realistic lens flare, "
        "imperfect lighting, volumetric light, soft shadows, "
        f"scene: {heading}. "
        f"location: {location}. time: {time_of_day}. "
        f"mood: {mood}. {keywords}. "
        f"{action}"
    )

    negative = (
        "illustration, cartoon, anime, painting, drawing, stylized art, "
        "CGI render, 3D render, concept art, fantasy art, flat design, "
        "oversaturated, perfect lighting, studio backdrop, watermark"
    )

    return positive.strip(), negative.strip()


# ── Image generation ──────────────────────────────────────────

def generate_cinematic_image(
    scene_data: dict,
    output_path: Path,
    size: str = "1792x1024",
) -> Optional[str]:
    """
    Generate a photorealistic cinematic frame via Seedream.
    Returns local file path on success, None on failure.
    """
    if not AVAILABLE:
        logger.error("BYTEPLUS_API_KEY not set")
        return None

    positive, negative = build_cinematic_prompt(scene_data)

    headers = {
        "Authorization": f"Bearer {BYTEPLUS_API_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":           IMAGE_MODEL,
        "prompt":          positive,
        "negative_prompt": negative,
        "size":            fit_size(size),
        "n":               1,
        "response_format": "url",
        # BytePlus stamps "AI generated" unless disabled
        "watermark":       os.getenv("JIMENG_WATERMARK", "false").lower() == "true",
    }

    try:
        resp = requests.post(
            f"{BYTEPLUS_BASE_URL}/images/generations",
            json=payload,
            headers=headers,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        url = data["data"][0]["url"]
        img_bytes = requests.get(url, timeout=30).content
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(img_bytes)
        logger.info(f"✅ Image saved: {output_path}")
        return str(output_path)

    except Exception as e:
        logger.error(f"❌ Image generation failed: {type(e).__name__}: {e}")
        return None


# ── Video generation (async task) ─────────────────────────────

def generate_cinematic_video(
    prompt: str,
    image_url: Optional[str] = None,
    duration: int = 5,
    resolution: str = "720p",
    poll_interval: int = 5,
    timeout: int = 300,
) -> Optional[str]:
    """
    Generate video via Seadance 2 (image-to-video if image_url provided,
    else text-to-video). Returns video URL on success, None on failure.
    """
    if not AVAILABLE:
        logger.error("BYTEPLUS_API_KEY not set")
        return None

    model = VIDEO_MODEL_I2V if image_url else VIDEO_MODEL_T2V

    content = [{"type": "text", "text": prompt}]
    if image_url:
        content.append({
            "type":      "image_url",
            "image_url": {"url": image_url},
        })

    headers = {
        "Authorization": f"Bearer {BYTEPLUS_API_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":   model,
        "content": content,
        "parameters": {
            "duration":   duration,
            "resolution": resolution,
        },
    }

    try:
        resp = requests.post(
            f"{BYTEPLUS_BASE_URL}/contents/generations/tasks",
            json=payload,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        task_id = resp.json()["id"]
        logger.info(f"📹 Seadance task submitted: {task_id}")
    except Exception as e:
        logger.error(f"❌ Video task submission failed: {e}")
        return None

    # Poll until done
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(poll_interval)
        try:
            r = requests.get(
                f"{BYTEPLUS_BASE_URL}/contents/generations/tasks/{task_id}",
                headers=headers,
                timeout=15,
            )
            r.raise_for_status()
            task = r.json()
            status = task.get("status", "")
            logger.info(f"  task {task_id} status: {status}")

            if status == "succeeded":
                content = task.get("content") or {}
                if isinstance(content, dict):      # {"video_url": "https://..."}
                    url = content.get("video_url")
                    return url.get("url") if isinstance(url, dict) else url
                for item in content:               # [{"type": "video_url", ...}]
                    if item.get("type") == "video_url":
                        return item["video_url"]["url"]
                return None

            if status in ("failed", "cancelled"):
                logger.error(f"❌ Task {task_id} ended: {status} — {task.get('error')}")
                return None

        except Exception as e:
            logger.warning(f"⚠️ Poll error: {e}")

    logger.error(f"❌ Timed out waiting for task {task_id}")
    return None


# ── Status check ──────────────────────────────────────────────

def get_status() -> dict:
    return {
        "available":   AVAILABLE,
        "base_url":    BYTEPLUS_BASE_URL,
        "image_model": IMAGE_MODEL,
        "video_i2v":   VIDEO_MODEL_I2V,
        "video_t2v":   VIDEO_MODEL_T2V,
    }
