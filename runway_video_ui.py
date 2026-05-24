#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎥 Runway Video Generation UI Component
For AI Studio Elsewhere - AI Film Director Interface

Integrates with runway_video_agent.py
"""

import streamlit as st
import subprocess
import os
import tempfile
from pathlib import Path
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

try:
    from runway_video_agent import (
        RunwayVideoAgent, VideoGenRequest, VideoGenResult,
        get_runway_agent
    )
    RUNWAY_AVAILABLE = True
except ImportError:
    RUNWAY_AVAILABLE = False
    logger.warning("⚠️ Runway Video Agent not available")

# ============================================================
# DIRECTOR PROMPT ENGINE
# ============================================================

_DIRECTOR_STYLES = {
    "Cinematic": {
        "base": "Cinematic film. Shallow depth of field. Film grain. Professional lighting.",
        "motion": "Slow deliberate camera movement. Gradual environmental shifts.",
    },
    "Dynamic": {
        "base": "Kinetic film aesthetic. High contrast. Physical tension.",
        "motion": "Handheld urgency. Quick angle shifts. Reactive camera.",
    },
    "Experimental": {
        "base": "Arthouse cinema. Unconventional framing. Poetic visual logic.",
        "motion": "Time dilation. Abstract motion. Fragmented perception.",
    },
    "Noir": {
        "base": "Black and white. 1940s film noir. High contrast shadows. Volumetric light.",
        "motion": "Slow dolly. Dust particles. Light flickering. Shadow movement.",
    },
}

_SHOT_CAMERAS = {
    "wide":   "Slow dolly forward from wide establishing shot. Architectural stillness.",
    "push":   "Gradual push-in toward focal point. Subtle handheld vibration.",
    "detail": "Static close-up of environmental detail. Light changing across surface.",
    "close":  "Slow rack focus to face or object. Breathing depth-of-field shift.",
}

_CLASSIFICATION_CAMERA = {
    "ATMOSPHERIC": "slow dolly forward, dust particles in air, light flickering, environmental breath",
    "ACTION":      "handheld movement, quick push-in, dynamic angle shift, wind and debris",
    "EMOTIONAL":   "slow close-up, shallow depth of field, soft focus, barely perceptible breathing motion",
    "DIALOGUE":    "subtle push-in on face, slight handheld sway, rack focus between subjects",
    "EXPOSITION":  "slow wide pan, architectural framing, deliberate spatial reveal",
    "TRANSITION":  "slow pull-back, ambient drift, temporal softness",
}


def generate_shot_sequence(scene: Dict) -> List[Dict]:
    """Generate 4-shot director sequence from scene data."""
    classification = scene.get("classification", "ATMOSPHERIC")
    heading = scene.get("heading", "Scene")

    shots = [
        {"type": "wide",   "label": "Establishing",
         "description": f"Wide establishing shot — {heading}"},
        {"type": "push",   "label": "Movement",
         "description": f"Push toward focal point — {heading}"},
        {"type": "detail", "label": "Atmosphere",
         "description": f"Environmental detail — light, texture, space"},
        {"type": "close",  "label": "Tension",
         "description": f"Close — final frame holds in still tension"},
    ]

    # Add camera from classification
    camera_base = _CLASSIFICATION_CAMERA.get(classification, _CLASSIFICATION_CAMERA["ATMOSPHERIC"])
    for shot in shots:
        shot["camera"] = _SHOT_CAMERAS[shot["type"]]
        shot["classification_camera"] = camera_base

    return shots


def build_cinematic_video_prompt(scene: Dict, shot: Dict, director_style: str = "Cinematic") -> str:
    """Build director-language video prompt from scene + shot type + style."""
    style_cfg = _DIRECTOR_STYLES.get(director_style, _DIRECTOR_STYLES["Cinematic"])
    heading    = scene.get("heading", "Scene")
    action     = scene.get("prompt", "")[:200]
    camera     = shot.get("camera", _SHOT_CAMERAS["wide"])
    motion_env = (
        "Doors moving in wind. Shadows shifting across surfaces. "
        "Fabric or objects reacting to environment. Subtle presence implied."
    )
    shot_sequence = (
        "Shot sequence: "
        "1. Wide establishing. "
        "2. Slow push toward doorway or focal point. "
        "3. Light entering through opening. "
        "4. Final frame holds in still tension."
    )

    return (
        f"{style_cfg['base']}\n\n"
        f"Scene: {heading}\n\n"
        f"Description: {action}\n\n"
        f"Camera: {camera}\n\n"
        f"Motion: {style_cfg['motion']} {motion_env}\n\n"
        f"{shot_sequence}"
    )


# ============================================================
# FFMPEG PIPELINE
# ============================================================

COLOR_GRADES = {
    "None":          None,
    "Cinematic Warm": "eq=saturation=1.1:gamma_r=1.08:gamma_b=0.94",
    "Noir B&W":      "hue=s=0,eq=contrast=1.35:brightness=-0.05",
    "Dream Blue":    "eq=saturation=0.8:gamma_b=1.12:gamma_r=0.95",
    "Vintage Film":  "curves=vintage",
}


def _ffmpeg_available() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def stitch_videos(video_paths: List[str], output_path: str) -> Optional[str]:
    """Concatenate video files with ffmpeg. Returns output path or None."""
    if not _ffmpeg_available():
        return None
    valid = [p for p in video_paths if Path(p).exists()]
    if not valid:
        return None
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for p in valid:
            f.write(f"file '{p}'\n")
        concat_file = f.name
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", concat_file, "-c", "copy", output_path],
            capture_output=True, timeout=120
        )
        os.unlink(concat_file)
        return output_path if Path(output_path).exists() else None
    except Exception:
        return None


def apply_color_grade(video_path: str, grade_filter: str, output_path: str) -> Optional[str]:
    """Apply ffmpeg color grade filter. Returns output path or None."""
    if not _ffmpeg_available() or not Path(video_path).exists():
        return None
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", video_path,
             "-vf", grade_filter, "-c:a", "copy", output_path],
            capture_output=True, timeout=120
        )
        return output_path if Path(output_path).exists() else None
    except Exception:
        return None


# ============================================================
# TIMELINE BAR
# ============================================================

def _timeline_bar(shots: List[Dict], generated: Dict) -> str:
    """ASCII timeline bar — filled if clip exists, empty if not."""
    bar = ""
    for shot in shots:
        stype = shot["type"]
        filled = stype in generated and generated[stype]
        bar += ("█" if filled else "░") * 4 + " "
    return bar.strip()

