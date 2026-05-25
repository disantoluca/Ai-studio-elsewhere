#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ElevenLabs ambient sound generation.
API key: ELEVENLABS_API_KEY env var.
"""

import os
import uuid
import logging
import tempfile
import requests
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
_URL = "https://api.elevenlabs.io/v1/sound-generation"
AVAILABLE = bool(ELEVENLABS_API_KEY)


def generate_ambient_sound(
    prompt: str,
    duration_seconds: float = 5.0,
    prompt_influence: float = 0.3,
) -> Optional[str]:
    """
    Generate ambient sound via ElevenLabs sound-generation API.
    Returns local mp3 path on success, None on failure.
    """
    if not AVAILABLE:
        logger.warning("ELEVENLABS_API_KEY not set")
        return None
    try:
        resp = requests.post(
            _URL,
            json={
                "text": prompt,
                "duration_seconds": duration_seconds,
                "prompt_influence": prompt_influence,
            },
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            timeout=60,
        )
        resp.raise_for_status()
        dest = Path(tempfile.gettempdir()) / f"ambient_{uuid.uuid4().hex[:8]}.mp3"
        dest.write_bytes(resp.content)
        logger.info(f"Ambient audio saved: {dest}")
        return str(dest)
    except Exception as e:
        logger.error(f"ElevenLabs sound generation failed: {e}")
        return None


def get_status() -> dict:
    return {"available": AVAILABLE, "endpoint": _URL}
