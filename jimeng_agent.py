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
    "https://ark.ap-southeast-1.bytepluses.com/api/v3"
)

# Model IDs — find yours in the Ark console under "Model Endpoints"
# Image (text-to-image): doubao-seedream-3-0-t2i-250415 or your endpoint ID
IMAGE_MODEL = os.getenv("BYTEPLUS_IMAGE_MODEL", "doubao-seedream-3-0-t2i-250415")

# Video (image-to-video): seedance-2-pro-x2v-250518 or your endpoint ID
VIDEO_MODEL_I2V = os.getenv("BYTEPLUS_VIDEO_MODEL_I2V", "seedance-2-pro-x2v-250518")

# Video (text-to-video): seedance-2-pro-t2v-250518 or your endpoint ID
VIDEO_MODEL_T2V = os.getenv("BYTEPLUS_VIDEO_MODEL_T2V", "seedance-2-pro-t2v-250518")

AVAILABLE = bool(BYTEPLUS_API_KEY)


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
        "size":            size,
        "n":               1,
        "response_format": "url",
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
                videos = task.get("content", [])
                for item in videos:
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
