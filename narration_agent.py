#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multilingual cinematic narration via GPT + OpenAI TTS.
API key: OPENAI_API_KEY env var (shared with concept-art pipeline).
"""

import os
import uuid
import logging
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AVAILABLE = bool(OPENAI_API_KEY)

LANGUAGES = {
    "English": {"code": "en", "voice": "nova"},
    "Chinese": {"code": "zh", "voice": "shimmer"},
    "French":  {"code": "fr", "voice": "fable"},
    "Thai":    {"code": "th", "voice": "alloy"},
}

_LANG_NAMES = {v["code"]: k for k, v in LANGUAGES.items()}


def _client():
    from openai import OpenAI
    return OpenAI(api_key=OPENAI_API_KEY)


def generate_narration_text(scene_heading: str, scene_description: str, language_code: str) -> Optional[str]:
    """Ask GPT to write one poetic sentence of cinematic narration in the target language."""
    if not AVAILABLE:
        return None
    lang_name = _LANG_NAMES.get(language_code, "English")
    try:
        resp = _client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a cinematographer writing on-screen narration for a film. "
                        f"Write exactly one sentence in {lang_name}. "
                        f"Maximum 20 words. Evocative, poetic, atmospheric. "
                        f"No exposition — only sensation and presence."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Scene: {scene_heading}\n{scene_description[:300]}",
                },
            ],
            max_tokens=80,
            temperature=0.75,
        )
        return resp.choices[0].message.content.strip().strip('"')
    except Exception as e:
        logger.error(f"Narration text generation failed: {e}")
        return None


def generate_narration_audio(text: str, voice: str) -> Optional[str]:
    """OpenAI TTS → local mp3. Returns path or None."""
    if not AVAILABLE:
        return None
    try:
        dest = Path(tempfile.gettempdir()) / f"narration_{uuid.uuid4().hex[:8]}.mp3"
        resp = _client().audio.speech.create(model="tts-1", voice=voice, input=text)
        resp.stream_to_file(str(dest))
        logger.info(f"Narration audio saved: {dest}")
        return str(dest)
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        return None


def generate_narration(scene_heading: str, scene_description: str, language: str) -> dict:
    """Full pipeline: scene → GPT text → TTS audio. Returns dict with text/audio_path/error."""
    out = {"text": None, "audio_path": None, "error": None}
    if language not in LANGUAGES:
        out["error"] = f"Unsupported language: {language}"
        return out
    lang = LANGUAGES[language]
    text = generate_narration_text(scene_heading, scene_description, lang["code"])
    if not text:
        out["error"] = "GPT narration text generation failed"
        return out
    out["text"] = text
    audio_path = generate_narration_audio(text, lang["voice"])
    if not audio_path:
        out["error"] = "TTS audio generation failed"
        return out
    out["audio_path"] = audio_path
    return out


def get_status() -> dict:
    return {"available": AVAILABLE, "languages": list(LANGUAGES.keys())}
