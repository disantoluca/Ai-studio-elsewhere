#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 AI Studio Elsewhere (云上电影工作室)
====================================
A fully integrated AI cinematic laboratory for film directors.

Features:
- Script upload (PDF, Word, TXT, images)
- OCR text extraction + image extraction
- Chinese ↔ English + Pinyin translation
- Scene breakdown & analysis
- Concept image generation (Wanxiang)
- Experimental video generation (Runway)
- Storyboard assembly
- Real-location research
- Export center

Director-first design: visual thinking, rapid experimentation, no technical complexity.
"""

import json
import os
import sys
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import io
import zipfile
import base64
from typing import Dict, List, Optional, Any, Tuple
from storyboard_ui import display_storyboard_ui
from storyboard_pdf_ui import display_pdf_export_ui, create_pdf_export_settings

# Demo project
try:
    from demo_project import load_demo_project
    DEMO_AVAILABLE = True
except ImportError:
    DEMO_AVAILABLE = False

# Google Places for location scouting
try:
    from google_places_agent import GooglePlacesAgent
    PLACES_AVAILABLE = True
except ImportError:
    PLACES_AVAILABLE = False

# ===========================================
# Core Dependencies
# ===========================================

import streamlit as st
from PIL import Image
import requests

# ============================================================
# Subscription System
# ============================================================

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False

# Load environment
from dotenv import load_dotenv
from pathlib import Path
import sys

# Try loading from multiple locations
env_paths = [
    Path.cwd() / ".env",
    Path(__file__).parent / ".env",
    Path.home() / ".env",
]

env_loaded = False
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path, override=True)
        print(f"✅ Loaded .env from: {env_path}")
        env_loaded = True
        break

if not env_loaded:
    # Fallback to default load_dotenv
    load_dotenv(override=True)
    print(f"⚠️ .env not found in standard locations, using defaults")

# Verify APIs are loaded
print("\n📋 API Configuration Status:")
print(f"   OPENAI_API_KEY: {'✅' if os.getenv('OPENAI_API_KEY') else '❌'}")
print(f"   RUNWAY_API_KEY: {'✅' if os.getenv('RUNWAY_API_KEY') else '❌'}")
print(f"   ANTHROPIC_API_KEY: {'✅' if os.getenv('ANTHROPIC_API_KEY') else '❌'}")
print(f"   DASHSCOPE_API_KEY: {'✅' if os.getenv('DASHSCOPE_API_KEY') else '❌'}")
print(f"   STRIPE_SECRET_KEY: {'✅' if os.getenv('STRIPE_SECRET_KEY') else '❌'}")
print()

# ============================================================
# SUBSCRIPTION MANAGER
# ============================================================

class SubscriptionManager:
    """Manage user subscriptions and feature access"""
    
    TIERS = {
        "free": {
            "name": "Free",
            "price": "$0",
            "concept_images": False,
            "video_generation": False,
            "batch_generation": False,
            "export": False,
        },
        "pro": {
            "name": "Pro",
            "price": "$9.99/mo",
            "concept_images": True,
            "video_generation": True,
            "batch_generation": False,
            "export": True,
        },
        "studio": {
            "name": "Studio",
            "price": "$49.99/mo",
            "concept_images": True,
            "video_generation": True,
            "batch_generation": True,
            "export": True,
        },
    }
    
    def __init__(self):
        self.stripe_key = os.getenv("STRIPE_SECRET_KEY")
        if self.stripe_key and STRIPE_AVAILABLE:
            stripe.api_key = self.stripe_key
            self.available = True
        else:
            self.available = False
    
    def get_user_tier(self) -> str:
        """Get current user's tier from session"""
        return st.session_state.get("user_tier", "free")
    
    def has_feature(self, feature: str) -> bool:
        """Check if user has access to a feature"""
        tier = self.get_user_tier()
        tier_config = self.TIERS.get(tier, {})
        return tier_config.get(feature, False)
    
    def get_checkout_url(self, tier: str, email: str) -> str:
        """Get Stripe checkout URL"""
        if not self.available or tier == "free":
            return ""
        
        try:
            price_map = {"pro": 999, "studio": 4999}  # cents
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"AI Studio Elsewhere - {self.TIERS[tier]['name']}",
                        },
                        "unit_amount": price_map.get(tier, 999),
                        "recurring": {"interval": "month"},
                    },
                    "quantity": 1,
                }],
                mode="subscription",
                customer_email=email,
                success_url="https://aistudioelsewhere.com/success",
                cancel_url="https://aistudioelsewhere.com/cancel",
            )
            return session.url
        except Exception as e:
            print(f"❌ Stripe error: {e}")
            return ""

# Initialize subscription manager
subscription_manager = SubscriptionManager()

# Initialize user session
if "user_id" not in st.session_state:
    st.session_state.user_id = "admin_lucadisanto"
    st.session_state.user_email = "ldisanto3@gmail.com"
    st.session_state.user_tier = "studio"
    st.session_state.is_admin = True

# OpenAI for translation & text processing
_openai_init_error = None
try:
    from openai import OpenAI as _OpenAI
    _openai_api_key = os.getenv("OPENAI_API_KEY")
    if _openai_api_key:
        openai_client = _OpenAI(api_key=_openai_api_key)
        print(f"[AI Studio] OpenAI client initialized OK (key prefix: {_openai_api_key[:8]}...)")
    else:
        openai_client = None
        _openai_init_error = "OPENAI_API_KEY not found in environment"
        print(f"[AI Studio] OpenAI client NOT initialized: OPENAI_API_KEY missing")
except Exception as e:
    openai_client = None
    _openai_init_error = str(e)
    print(f"[AI Studio] OpenAI client init FAILED: {e}")

# Runway Characters (Latest GWM-1)
try:
    from runway_characters_ui import display_character_creation_tab, display_character_management
    CHARACTERS_AVAILABLE = True
except ImportError:
    CHARACTERS_AVAILABLE = False
    print("⚠️ Runway Characters module not available")

# PDF processing
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    print("⚠️ pdf2image not available. PDF processing disabled.")
    PDF2IMAGE_AVAILABLE = False

# OCR for text extraction
try:
    import easyocr
    EASYOCR_AVAILABLE = True
    _ocr_reader = None
except ImportError:
    print("⚠️ EasyOCR not available. OCR disabled.")
    EASYOCR_AVAILABLE = False
    _ocr_reader = None

# PyMuPDF — fast PDF text extraction (preferred path)
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    print("⚠️ PyMuPDF not available. Install: pip install pymupdf")
    PYMUPDF_AVAILABLE = False

MAX_PAGES = 10  # Process only first N pages — 80-90% speed gain

# Vision for image analysis (Phase 2 - optional)
try:
    from transformers import AutoProcessor, AutoModelForVision2Seq
    import torch
    VISION_AVAILABLE = True
    _vision_processor = None
    _vision_model = None
except ImportError:
    VISION_AVAILABLE = False
    _vision_processor = None
    _vision_model = None

# Runway for video generation (Phase 2 - optional)
try:
    import runway
    RUNWAY_AVAILABLE = True
except ImportError:
    RUNWAY_AVAILABLE = False

# Wanxiang for image generation (concept art mode)
try:
    from tongyi_wanx_client import TongyiWanxClient
    WANX_AVAILABLE = True
except ImportError:
    WANX_AVAILABLE = False

# Byteplus / Seadance for cinematic realism mode
try:
    import jimeng_agent as _jimeng
    JIMENG_AVAILABLE = _jimeng.AVAILABLE
except Exception:
    JIMENG_AVAILABLE = False

# ===========================================
# Configuration & Paths
# ===========================================

BASE_DIR = Path(__file__).parent
# DATA_DIR can be overridden via env var so Railway Volumes survive redeploys
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
SCRIPTS_DIR   = DATA_DIR / "scripts"
SCENES_DIR    = DATA_DIR / "scenes"
CONCEPTS_DIR  = DATA_DIR / "concepts"
VIDEOS_DIR    = DATA_DIR / "videos"
STORYBOARDS_DIR = DATA_DIR / "storyboards"
EXPORTS_DIR   = DATA_DIR / "exports"

for d in [DATA_DIR, SCRIPTS_DIR, SCENES_DIR, CONCEPTS_DIR, VIDEOS_DIR, STORYBOARDS_DIR, EXPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ===========================================
# Data Structures
# ===========================================

@dataclass
class SceneBreakdown:
    """Represents a single scene from a script"""
    scene_id: str
    scene_number: int
    heading: str  # Scene heading (INT/EXT, LOCATION, TIME)
    location: str
    time_of_day: str
    characters: List[str]
    action: str
    dialogue: List[Tuple[str, str]]  # [(character, text), ...]
    image_paths: List[str] = None
    keywords: List[str] = None
    mood: str = ""
    scene_type: str = "STANDARD"    # STANDARD | INTERCUT | FLASHBACK | MONTAGE
    classification: str = "ATMOSPHERIC"  # ACTION | DIALOGUE | ATMOSPHERIC | EMOTIONAL | EXPOSITION | TRANSITION
    
    def __post_init__(self):
        if self.image_paths is None:
            self.image_paths = []
        if self.keywords is None:
            self.keywords = []

@dataclass
class Project:
    """Film project metadata"""
    project_id: str
    title_en: str
    title_zh: Optional[str]
    director: str
    logline: str
    created_at: str
    last_updated: str
    script_path: Optional[str]
    scenes: List[SceneBreakdown] = None
    concepts: Dict[str, List[str]] = None  # scene_id -> [image_urls]
    videos: Dict[str, str] = None  # scene_id -> video_url
    
    def __post_init__(self):
        if self.scenes is None:
            self.scenes = []
        if self.concepts is None:
            self.concepts = {}
        if self.videos is None:
            self.videos = {}

# ===========================================
# OCR Helper Functions
# ===========================================

def get_ocr_reader():
    """Lazily load EasyOCR reader"""
    global _ocr_reader
    if _ocr_reader is None and EASYOCR_AVAILABLE:
        # Fix: Chinese_tra requires English to be included
        _ocr_reader = easyocr.Reader(['ch_tra', 'en'], gpu=False)
    return _ocr_reader

def extract_text_from_image(image_path: str) -> str:
    """Extract text from image using OCR"""
    if not EASYOCR_AVAILABLE:
        return ""
    
    try:
        reader = get_ocr_reader()
        result = reader.readtext(image_path)
        text = "\n".join([item[1] for item in result])
        return text
    except Exception as e:
        print(f"❌ OCR error: {e}")
        return ""

# ===========================================
# PDF Processing Helper
# ===========================================

def extract_pages_from_pdf(pdf_path: str) -> Tuple[List[Image.Image], List[str]]:
    """Convert PDF to images, return (images, page_paths)"""
    if not PDF2IMAGE_AVAILABLE:
        return [], []
    
    try:
        images = convert_from_path(pdf_path, dpi=300)
        page_paths = []
        
        # Save pages as temporary PNGs
        for i, img in enumerate(images):
            page_path = SCRIPTS_DIR / f"temp_page_{i:04d}.png"
            img.save(page_path, "PNG")
            page_paths.append(str(page_path))
        
        return images, page_paths
    except Exception as e:
        st.error(f"❌ PDF extraction failed: {e}")
        return [], []

@st.cache_data(show_spinner=False)
def extract_text_fast(file_bytes: bytes) -> str:
    """Fast PDF text extraction using PyMuPDF. Cached — same file never processed twice."""
    if not PYMUPDF_AVAILABLE:
        return ""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        for i, page in enumerate(doc):
            if i >= MAX_PAGES:
                break
            page_text = page.get_text()
            if page_text.strip():
                text += page_text
        return text
    except Exception as e:
        print(f"❌ PyMuPDF error: {e}")
        return ""

def extract_text_pages(file_bytes: bytes, max_pages: int) -> tuple:
    """Extract text from PDF, up to max_pages. Returns (text, page_count)."""
    if not PYMUPDF_AVAILABLE:
        return "", 0
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        total_pages = len(doc)
        pages_text, pages_read = [], 0
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            t = page.get_text()
            if t.strip():
                pages_text.append(t)
            pages_read = i + 1
        return "\n".join(pages_text), pages_read
    except Exception as e:
        print(f"❌ PyMuPDF error: {e}")
        return "", 0

def _normalize_script_text(text: str) -> str:
    """Normalize dashes, whitespace, and Chinese scene markers for reliable parsing."""
    import re
    # Chinese scene markers → standard screenplay format
    chinese_map = {
        '内景': 'INT.',
        '外景': 'EXT.',
        '内/外景': 'INT./EXT.',
        '（': '(',
        '）': ')',
        '：': ':',
        '\u3000': ' ',  # ideographic space
    }
    for k, v in chinese_map.items():
        text = text.replace(k, v)
    text = text.replace('\u2013', '-').replace('\u2014', '-')  # en/em dash → hyphen
    text = re.sub(r'[ \t]+', ' ', text)                        # collapse multiple spaces
    return text


def extract_scene_blocks(text: str) -> list:
    """
    Robust scene extractor. Captures full INT./EXT. scene blocks.
    Tolerates em-dashes, irregular spacing, and non-standard formatting.
    Returns list of dicts: id, heading, body, type.
    """
    import re
    text = _normalize_script_text(text)
    header_re = re.compile(r'(?:^|\n)((?:INT\.|EXT\.)[^\n]+)', re.IGNORECASE | re.MULTILINE)
    matches = list(header_re.finditer(text))
    if not matches:
        return []
    scenes = []
    for i, m in enumerate(matches):
        heading = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        upper = (heading + ' ' + body).upper()
        if 'INTERCUT' in upper:
            scene_type = 'INTERCUT'
        elif 'FLASHBACK' in upper or 'FLASH BACK' in upper:
            scene_type = 'FLASHBACK'
        elif 'MONTAGE' in upper:
            scene_type = 'MONTAGE'
        else:
            scene_type = 'STANDARD'
        scenes.append({'id': i + 1, 'heading': heading, 'body': body[:400], 'type': scene_type})
    return scenes


def stream_scenes_from_text(text: str, max_pages: int = MAX_PAGES):
    """Thin wrapper — existing callers unchanged."""
    for s in extract_scene_blocks(text):
        yield {"id": s["id"], "heading": s["heading"], "action": s["body"][:200]}

# ===========================================
# Translation & Text Processing
# ===========================================

def translate_to_english(text_zh: str) -> str:
    """Translate Chinese text to English"""
    if not openai_client:
        return ""
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert film script translator. Translate Chinese film script text to English, preserving tone and cinematic intent."
                },
                {
                    "role": "user",
                    "content": f"Translate this to English:\n\n{text_zh}"
                }
            ],
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"⚠️ Translation error: {e}")
        return ""

def generate_pinyin(text_zh: str) -> str:
    """Generate pinyin romanization"""
    if not openai_client:
        return ""
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Generate pinyin romanization for Chinese text. Format: pinyin above each line of Chinese."
                },
                {
                    "role": "user",
                    "content": f"Generate pinyin for:\n{text_zh}"
                }
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"⚠️ Pinyin generation error: {e}")
        return ""

# ===========================================
# Scene Breakdown Engine
# ===========================================

def translate_scene_elements_to_english(heading: str, location: str, action: str, mood: str) -> Tuple[str, str, str, str]:
    """
    ⚡ OPTIMIZED: Skip translation for speed.
    Returns original text instantly instead of calling GPT-4o.
    This speeds up scene parsing from 5+ minutes to ~20 seconds!
    """
    # Fast path: return original (no API call needed)
    return heading, location, action, mood

def parse_script_to_scenes(text: str, translate: bool = False) -> List[SceneBreakdown]:
    """
    Parse script text to individual scenes with optional translation.
    Uses regex for structure, GPT-4o-mini for enrichment.
    """
    # Always extract regex blocks first — they are the floor for all failure paths
    blocks = extract_scene_blocks(text)

    def _blocks_to_scenes(blocks_list):
        scenes = []
        for i, b in enumerate(blocks_list):
            scene = SceneBreakdown(
                scene_id=f"scene_{i+1:03d}",
                scene_number=b["id"],
                heading=b["heading"],
                location="",
                time_of_day="",
                characters=[],
                action=b["body"],
                dialogue=[],
                keywords=[],
                mood="",
                scene_type=b.get("type", "STANDARD"),
            )
            scene.classification = classify_scene(scene)
            scenes.append(scene)
        return scenes

    if not openai_client:
        return _blocks_to_scenes(blocks) if blocks else []

    try:
        # Build condensed input for GPT from already-extracted blocks
        if blocks:
            condensed = "\n\n".join(
                f"SCENE {b['id']}: {b['heading']}\n{b['body'][:300]}"
                for b in blocks[:20]
            )
            gpt_input = condensed
        else:
            # No INT./EXT. found — send raw text (prose scripts, treatments)
            gpt_input = text[:8000]

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a film script analyst. "
                        "Extract scenes from this script and return a JSON array. "
                        "Each element must have: scene_number, heading, location, "
                        "time_of_day, characters (array), action, keywords (array), mood. "
                        "Return ONLY valid JSON — no markdown fences, no commentary."
                    )
                },
                {
                    "role": "user",
                    "content": f"Parse this script:\n\n{gpt_input}"
                }
            ],
            max_tokens=3000,
            temperature=0.5
        )
        
        json_str = response.choices[0].message.content

        # Strip markdown fences GPT sometimes adds despite instructions
        import re as _re
        json_str = _re.sub(r'^```(?:json)?\s*', '', json_str.strip(), flags=_re.IGNORECASE)
        json_str = _re.sub(r'\s*```$', '', json_str.strip())
        # Extract first JSON array if there is surrounding commentary
        arr_match = _re.search(r'\[[\s\S]*\]', json_str)
        if arr_match:
            json_str = arr_match.group()

        try:
            scenes_data = json.loads(json_str)
        except:
            scenes_data = []

        # GPT returned empty array or JSON failed — fall back to regex blocks
        if not scenes_data and blocks:
            scenes_data = [
                {
                    "scene_number": b["id"],
                    "heading": b["heading"],
                    "location": "",
                    "time_of_day": "",
                    "characters": [],
                    "action": b["body"],
                    "keywords": [],
                    "mood": "",
                    "_from_regex": True,
                }
                for b in blocks
            ]
        elif not scenes_data:
            # No blocks either — single-scene fallback
            scenes_data = [
                {
                    "scene_number": 1,
                    "heading": "OPENING SCENE",
                    "location": "TBD",
                    "time_of_day": "Unknown",
                    "characters": [],
                    "action": text[:500],
                    "keywords": ["establishing"],
                    "mood": "neutral",
                }
            ]
        
        scenes = []
        
        for i, scene_data in enumerate(scenes_data):
            heading = scene_data.get("heading", "SCENE")
            location = scene_data.get("location", "")
            action = scene_data.get("action", "")
            mood = scene_data.get("mood", "")
            
            # Optionally translate (skip by default for speed)
            if translate:
                heading, location, action, mood = translate_scene_elements_to_english(
                    heading, location, action, mood
                )
            
            # Derive scene_type from regex blocks if available
            block_type = "STANDARD"
            if blocks and i < len(blocks):
                block_type = blocks[i].get("type", "STANDARD")
            else:
                # Infer from action text
                action_upper = action.upper()
                if "INTERCUT" in action_upper:
                    block_type = "INTERCUT"
                elif "FLASHBACK" in action_upper or "FLASH BACK" in action_upper:
                    block_type = "FLASHBACK"
                elif "MONTAGE" in action_upper:
                    block_type = "MONTAGE"

            scene = SceneBreakdown(
                scene_id=f"scene_{i+1:03d}",
                scene_number=scene_data.get("scene_number", i+1),
                heading=heading,
                location=location,
                time_of_day=scene_data.get("time_of_day", ""),
                characters=scene_data.get("characters", []),
                action=action,
                dialogue=[],
                keywords=scene_data.get("keywords", []),
                mood=mood,
                scene_type=block_type,
            )
            scene.classification = classify_scene(scene)
            scenes.append(scene)

        return scenes
    
    except Exception as e:
        st.warning(f"⚠️ GPT enrichment failed ({e}) — using regex structure")
        return _blocks_to_scenes(blocks) if blocks else []

# ===========================================
# Scene Prompt Auto-Builder
# ===========================================

def build_scene_prompts(scene) -> dict:
    """
    Rule-based cinematic prompt builder. Instant — no API.
    Returns visual_prompt, video_prompt, mood, location, camera.
    """
    heading = getattr(scene, 'heading', '') if not isinstance(scene, dict) else scene.get('heading', '')
    action  = getattr(scene, 'action',  '') if not isinstance(scene, dict) else scene.get('action',  '')
    mood_in = getattr(scene, 'mood',    '') if not isinstance(scene, dict) else scene.get('mood',    '')
    loc_in  = getattr(scene, 'location','') if not isinstance(scene, dict) else scene.get('location','')

    text = (heading + ' ' + action + ' ' + mood_in).lower()

    # Location
    if loc_in:
        location = loc_in
    elif 'tram' in text or 'train' in text:
        location = 'night tram interior'
    elif 'street' in text or 'alley' in text:
        location = 'urban street at night'
    elif 'room' in text or 'apartment' in text or 'int.' in text:
        location = 'interior room'
    elif 'ext.' in text:
        location = 'exterior environment'
    else:
        location = 'cinematic environment'

    # Mood
    mood = []
    if mood_in:
        mood.append(mood_in)
    if 'night' in text:
        mood.append('dark')
    if 'alone' in text or 'empty' in text:
        mood.append('lonely')
    if 'memory' in text or 'past' in text or 'remember' in text:
        mood.append('nostalgic')
    if 'dream' in text or 'surreal' in text:
        mood.append('dreamlike')
    if not mood:
        mood = ['cinematic', 'emotional']
    mood = list(dict.fromkeys(mood))  # dedupe, preserve order

    mood_str = ', '.join(mood)
    visual_prompt = (
        f"{location}, {mood_str}, cinematic lighting, soft shadows, "
        f"film still, shallow depth of field, poetic realism"
    )
    video_prompt = (
        f"{location}, {mood_str}, cinematic motion, slow camera movement, "
        f"realistic lighting, film scene, subtle emotion"
    )

    # Camera
    if 'walk' in text or 'enter' in text or 'move' in text:
        camera = 'slow dolly-in'
    elif 'look' in text or 'see' in text or 'watch' in text:
        camera = 'close-up'
    elif 'memory' in text or 'dream' in text:
        camera = 'floating camera'
    else:
        camera = 'static cinematic shot'

    video_prompt += f', {camera}'

    # Scene-type enhancement — film grammar shapes the prompt
    scene_type = getattr(scene, 'scene_type', 'STANDARD') if not isinstance(scene, dict) else scene.get('type', 'STANDARD')
    if scene_type == 'INTERCUT':
        visual_prompt += ', parallel action, cross-cutting composition'
        video_prompt += ', dynamic cross-cutting, parallel timelines'
    elif scene_type == 'FLASHBACK':
        visual_prompt += ', soft nostalgic lighting, memory haze, desaturated'
        video_prompt += ', nostalgic tone, soft diffusion, memory atmosphere'
    elif scene_type == 'MONTAGE':
        visual_prompt += ', sequence composition, rhythmic visual structure'
        video_prompt += ', fast cuts, compressed time, rhythmic editing'

    return {
        'location': location,
        'mood': mood,
        'visual_prompt': visual_prompt,
        'video_prompt': video_prompt,
        'camera': camera,
        'scene_type': scene_type,
    }

# ===========================================
# Director Intelligence Engine
# ===========================================

def classify_scene(scene) -> str:
    """Rule-based scene classification. Instant — no API."""
    text = (
        (getattr(scene, 'action', '') or '') + ' ' +
        (getattr(scene, 'mood', '') or '') + ' ' +
        (getattr(scene, 'heading', '') or '')
    ).lower() if not isinstance(scene, dict) else (
        scene.get('action', '') + ' ' + scene.get('mood', '') + ' ' + scene.get('heading', '')
    ).lower()

    scores = {
        'ACTION': 0, 'DIALOGUE': 0, 'ATMOSPHERIC': 0,
        'TRANSITION': 0, 'EMOTIONAL': 0, 'EXPOSITION': 0,
    }
    action_words = ['runs', 'crashes', 'tears', 'explodes', 'storm', 'fight', 'chase', 'breaks']
    dialogue_words = ['says', 'asks', 'replies', 'whispers', 'shouts', 'tells', 'conversation']
    atm_words = ['wind', 'rain', 'dark', 'light', 'sea', 'silence', 'fog', 'mist', 'sky', 'empty']
    trans_words = ['intercut', 'cut to', 'montage', 'fade', 'dissolve', 'smash cut']
    emo_words = ['alone', 'memory', 'fear', 'love', 'cry', 'grief', 'longing', 'tenderness']
    expo_words = ['explains', 'history', 'background', 'tells us', 'years ago', 'long before']
    for w in action_words:
        if w in text: scores['ACTION'] += 2
    for w in dialogue_words:
        if w in text: scores['DIALOGUE'] += 2
    for w in atm_words:
        if w in text: scores['ATMOSPHERIC'] += 2
    for w in trans_words:
        if w in text: scores['TRANSITION'] += 3
    for w in emo_words:
        if w in text: scores['EMOTIONAL'] += 2
    for w in expo_words:
        if w in text: scores['EXPOSITION'] += 2
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else 'ATMOSPHERIC'


def generate_shot_list(classification: str) -> list:
    """Return a standard shot list for a given scene classification."""
    SHOTS = {
        'ACTION':      ['Wide establishing shot', 'Handheld tracking shot',
                        'Close-up — impact moment', 'Fast cut reaction shot'],
        'DIALOGUE':    ['Shot-reverse-shot', 'Medium two-shot',
                        'Close-up — emotional beats', 'Over-the-shoulder framing'],
        'ATMOSPHERIC': ['Wide static shot', 'Slow pan',
                        'Detail shot — environment', 'Long take'],
        'EMOTIONAL':   ['Close-up — face', 'Extreme close-up — eyes/hands',
                        'Slow dolly-in', 'Soft focus wide shot'],
        'TRANSITION':  ['Match cut', 'Cross dissolve',
                        'Symbolic insert shot', 'Wide transition frame'],
        'EXPOSITION':  ['Master shot', 'Establishing wide',
                        'Insert shot — detail', 'Slow pull-back'],
    }
    return SHOTS.get(classification, ['Wide shot', 'Medium shot', 'Close-up'])


def detect_weak_scene(scene) -> list:
    """Return list of issue strings, or [] if scene is strong."""
    action = getattr(scene, 'action', '') or '' if not isinstance(scene, dict) else scene.get('action', '') or ''
    issues = []
    if len(action.strip()) < 15:
        issues.append('Scene needs development')
    return issues


def build_director_insights(scenes) -> dict:
    """Aggregate classification stats for the director dashboard."""
    if not scenes:
        return {}
    total = len(scenes)
    from collections import Counter
    counts = Counter(getattr(s, 'classification', 'ATMOSPHERIC') for s in scenes)
    weak_count = sum(1 for s in scenes if detect_weak_scene(s))
    dominant = counts.most_common(1)[0][0]
    emotional = counts.get('EMOTIONAL', 0) + counts.get('ATMOSPHERIC', 0)
    action = counts.get('ACTION', 0)
    pacing = 'contemplative' if emotional > action else 'dynamic' if action > emotional else 'balanced'
    return {
        'total': total,
        'counts': dict(counts),
        'weak': weak_count,
        'dominant': dominant,
        'pacing': pacing,
        'emotional_ratio': round(emotional / total, 2),
        'action_ratio': round(action / total, 2),
        'strength': round(1 - (weak_count / total), 2),
    }


_REWRITE_STYLES = {
    'Improve (general)':  'Improve emotional impact, cinematic clarity, and visual storytelling. Keep the original meaning.',
    'Wong Kar-wai':       'Fragmented narration, poetic voiceover, emotional isolation, slow time perception, visual metaphors, minimal dialogue.',
    'Tarkovsky':          'Long takes, natural textures, muted palette, philosophical tone, silence as meaning, spiritual weight.',
    'Enhance emotion':    'Deepen emotional resonance, add subtext, reduce exposition, let characters reveal through action.',
    'Cinematic action':   'Heighten physical tension, sharpen spatial clarity, punch up visual energy and kinetic rhythm.',
}

def rewrite_scene_ai(scene_text: str, style_label: str = 'Improve (general)') -> str:
    """AI scene rewrite using GPT-4o-mini. Returns rewritten text or error string."""
    if not openai_client:
        return '❌ OpenAI client not available'
    style_instruction = _REWRITE_STYLES.get(style_label, _REWRITE_STYLES['Improve (general)'])
    try:
        response = openai_client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'You are a professional film script doctor. '
                        'Rewrite the scene according to the given style instruction. '
                        'Output only the rewritten scene — no commentary, no headings.'
                    )
                },
                {
                    'role': 'user',
                    'content': f'Style: {style_instruction}\n\nScene:\n{scene_text[:1500]}'
                }
            ],
            max_tokens=800,
            temperature=0.75,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f'❌ Rewrite failed: {e}'


# ===========================================
# Concept Image Generation (Wanxiang)
# ===========================================

def generate_concept_images(scene: SceneBreakdown, style: str = "cinematic", project_id: str = "", mode: str = "concept", output_type: str = "Cinematic Frame (for video)", video_ready: bool = True) -> List[str]:
    """Generate concept images. mode='concept' uses Wanxiang; mode='cinematic' uses OpenAI/Byteplus."""

    concept_dir = CONCEPTS_DIR / (project_id or "default")
    concept_dir.mkdir(parents=True, exist_ok=True)
    safe_id = scene.scene_id.replace('/', '_')

    # ── Cinematic Realism mode ────────────────────────────────────────
    if mode == "cinematic":
        local_path = concept_dir / f"{safe_id}_cinematic.png"

        direction_map = {
            "natural realism":       "natural light, realistic textures, everyday physicality",
            "noir b&w":              "high contrast black and white, deep shadows, dramatic single-source light, 1940s atmosphere",
            "dreamlike":             "soft diffused light, hazy atmosphere, surreal gentle realism, ethereal quality",
            "gritty realism":        "harsh light, rough textures, grime and wear, raw documentary feel",
            "period film (1940s)":   "1940s period authentic, warm sepia tones, period-accurate details, classic Hollywood lighting",
            "poetic cinema":         "painterly naturalism, golden hour light, wide sky, long shadows, contemplative stillness",
        }
        output_map = {
            "cinematic frame (for video)": "ultra realistic film still, shot on ARRI Alexa, anamorphic lens",
            "storyboard frame":            "clear compositional storyboard, strong readable shapes",
            "reference photography":       "location photography reference, realistic environment, production design quality",
            "mood exploration":            "atmospheric mood study, evocative lighting, strong emotional tone",
        }
        direction_words = direction_map.get(style.lower(), "cinematic naturalism")
        output_words    = output_map.get(output_type.lower(), "cinematic film still")
        video_words = (
            "photorealistic, real-world physics, natural motion potential, "
            "no illustration, no painting, no stylization"
        ) if video_ready else ""

        prompt = (
            f"{output_words}. {direction_words}. "
            f"Scene: {scene.heading}. Location: {scene.location}, {scene.time_of_day}. "
            f"Mood: {scene.mood or 'dramatic'}. "
            f"{', '.join(scene.keywords) if scene.keywords else ''}. "
            f"{scene.action[:200]}. "
            f"Film grain, shallow depth of field, imperfect realistic lighting. {video_words}"
        ).strip()

        if openai_client:
            _image_models = [
                ("gpt-image-1", {"size": "1536x1024", "quality": "high"}),
                ("dall-e-3",    {"size": "1792x1024", "quality": "hd"}),
                ("dall-e-2",    {"size": "1024x1024"}),
            ]
            generated_url = None
            for _model, _params in _image_models:
                try:
                    response = openai_client.images.generate(
                        model=_model, prompt=prompt, n=1, **_params,
                    )
                    generated_url = response.data[0].url
                    break
                except Exception as e:
                    st.warning(f"⚠️ {_model} failed: {e}")
            if generated_url:
                img_bytes = requests.get(generated_url, timeout=30).content
                local_path.write_bytes(img_bytes)
                return [str(local_path)]
        else:
            st.warning(f"⚠️ OpenAI client not available — {_openai_init_error or 'OPENAI_API_KEY not set'}")

        if JIMENG_AVAILABLE:
            scene_data = {
                "heading": scene.heading, "location": scene.location,
                "time_of_day": scene.time_of_day, "mood": scene.mood,
                "keywords": scene.keywords, "action": scene.action,
            }
            result = _jimeng.generate_cinematic_image(scene_data, local_path)
            if result:
                return [result]

        st.error("❌ Cinematic generation failed — check OpenAI key or Byteplus activation.")
        return []

    # ── Concept Art mode (Wanxiang) ─────────────────────────────
    if not WANX_AVAILABLE or not os.getenv("DASHSCOPE_API_KEY"):
        st.warning("⚠️ Wanxiang API not configured. Skipping image generation.")
        return []

    try:
        from tongyi_wanx_client import TongyiWanxClient
        client = TongyiWanxClient()

        prompt = f"""
        Film scene concept art:

        Scene: {scene.heading}
        Location: {scene.location}
        Time: {scene.time_of_day}
        Mood: {scene.mood}
        Keywords: {", ".join(scene.keywords)}

        Action: {scene.action[:200]}

        Style: {style}
        Generate cinematic concept art for this scene.
        """

        result = client.generate_image(
            prompt=prompt,
            negative_prompt="blurry, watermark, low quality",
            seed=None
        )

        if result.get('status') == 'succeeded' and result.get('images'):
            urls = result['images']
            local_paths = []
            for j, url in enumerate(urls):
                local_path = concept_dir / f"{safe_id}_{j}.png"
                try:
                    img_data = requests.get(url, timeout=15).content
                    local_path.write_bytes(img_data)
                    local_paths.append(str(local_path))
                except Exception:
                    local_paths.append(url)
            return local_paths
        else:
            st.warning(f"⚠️ Image generation failed: {result.get('error', 'Unknown error')}")
            return []

    except Exception as e:
        st.error(f"❌ Concept generation error: {e}")
        return []

# ===========================================
# Video Generation (Runway - Stub for now)
# ===========================================

def generate_video_scene(scene: SceneBreakdown, concept_image_url: Optional[str] = None) -> Optional[str]:
    """
    Generate experimental video for a scene using Runway.
    Stub implementation - requires actual Runway API integration.
    """
    st.info("🎥 Video generation requires Runway API integration. Contact support.")
    return None

# ===========================================
# Project Management
# ===========================================

# ===========================================
# Persistent Storage (PostgreSQL → file fallback)
# ===========================================

DATABASE_URL = os.getenv("DATABASE_URL")
_db_error: str = ""


def _get_db_conn():
    global _db_error
    if not DATABASE_URL:
        _db_error = "DATABASE_URL not set"
        return None
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        _db_error = ""
        return conn
    except Exception as e:
        _db_error = str(e)
        return None


def _init_db():
    conn = _get_db_conn()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                project_id TEXT PRIMARY KEY,
                title_en   TEXT,
                data       TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()


_init_db()


def list_projects() -> List[str]:
    """Return list of project_ids, most recently updated first."""
    conn = _get_db_conn()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT project_id FROM projects ORDER BY updated_at DESC")
            ids = [row[0] for row in cur.fetchall()]
            conn.close()
            return ids
        except Exception:
            conn.close()
    # File fallback
    ids = [p.stem.replace("project_", "") for p in SCRIPTS_DIR.glob("project_*.json")]
    return sorted(ids)


def list_projects_with_titles() -> List[tuple]:
    """Return [(project_id, title_en), ...] most recently updated first."""
    conn = _get_db_conn()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT project_id, title_en FROM projects ORDER BY updated_at DESC")
            rows = cur.fetchall()
            conn.close()
            return [(r[0], r[1] or r[0]) for r in rows]
        except Exception:
            conn.close()
    # File fallback
    result = []
    for p in SCRIPTS_DIR.glob("project_*.json"):
        pid = p.stem.replace("project_", "")
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            result.append((pid, data.get("title_en") or pid))
        except Exception:
            result.append((pid, pid))
    return sorted(result, key=lambda x: x[1])


def load_project(project_id: str) -> Optional[Project]:
    """Load project — PostgreSQL first, file fallback."""

    def _reconstruct(data: dict) -> Project:
        scenes = []
        for s in (data.get("scenes") or []):
            if isinstance(s, dict):
                scenes.append(SceneBreakdown(
                    scene_id=s.get("scene_id", ""),
                    scene_number=s.get("scene_number", 0),
                    heading=s.get("heading", ""),
                    location=s.get("location", ""),
                    time_of_day=s.get("time_of_day", ""),
                    characters=s.get("characters", []),
                    action=s.get("action", ""),
                    dialogue=s.get("dialogue", []),
                    image_paths=s.get("image_paths", []),
                    keywords=s.get("keywords", []),
                    mood=s.get("mood", ""),
                    classification=s.get("classification", ""),
                    scene_type=s.get("scene_type", "STANDARD"),
                ))
        concepts = data.get("concepts", {})
        if not isinstance(concepts, dict):
            concepts = {}
        return Project(
            project_id=data.get("project_id"),
            title_en=data.get("title_en"),
            title_zh=data.get("title_zh"),
            director=data.get("director"),
            logline=data.get("logline"),
            created_at=data.get("created_at"),
            last_updated=data.get("last_updated"),
            script_path=data.get("script_path"),
            scenes=scenes,
            concepts=concepts,
        )

    conn = _get_db_conn()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT data FROM projects WHERE project_id = %s", (project_id,))
            row = cur.fetchone()
            conn.close()
            if row:
                return _reconstruct(json.loads(row[0]))
        except Exception:
            conn.close()

    # File fallback
    proj_file = SCRIPTS_DIR / f"project_{project_id}.json"
    if not proj_file.exists():
        return None
    try:
        return _reconstruct(json.loads(proj_file.read_text(encoding="utf-8")))
    except Exception as e:
        st.error(f"❌ Failed to load project: {e}")
        return None

def save_project(project: Project):
    """Save project — PostgreSQL first, file fallback."""
    data = {
        "project_id": project.project_id,
        "title_en": project.title_en,
        "title_zh": project.title_zh,
        "director": project.director,
        "logline": project.logline,
        "created_at": project.created_at,
        "last_updated": datetime.now().isoformat(),
        "script_path": project.script_path,
        "scenes": [
            {
                "scene_id": s.scene_id,
                "scene_number": s.scene_number,
                "heading": s.heading,
                "location": s.location,
                "time_of_day": s.time_of_day,
                "characters": s.characters,
                "action": s.action,
                "dialogue": s.dialogue,
                "image_paths": s.image_paths,
                "keywords": s.keywords,
                "mood": s.mood,
                "classification": getattr(s, 'classification', ''),
                "scene_type": getattr(s, 'scene_type', 'STANDARD'),
            }
            for s in project.scenes
        ],
        "concepts": project.concepts,
        "videos": list(project.videos.keys()),
    }
    json_str = json.dumps(data, ensure_ascii=False)

    conn = _get_db_conn()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO projects (project_id, title_en, data)
                VALUES (%s, %s, %s)
                ON CONFLICT (project_id)
                DO UPDATE SET title_en = %s, data = %s, updated_at = NOW()
            """, (project.project_id, project.title_en, json_str,
                  project.title_en, json_str))
            conn.commit()
            conn.close()
            return
        except Exception:
            conn.rollback()
            conn.close()

    # File fallback
    try:
        proj_file = SCRIPTS_DIR / f"project_{project.project_id}.json"
        with open(proj_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"❌ Failed to save project: {e}")

# ===========================================
# Streamlit UI
# ===========================================

st.set_page_config(
    page_title="AI Studio Elsewhere",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at 50% 20%, #161616, #0b0b0b);
    color: #f0ece4;
}
h1, h2, h3 { color: #f0ece4; font-weight: 400; letter-spacing: 0.02em; }
.stButton > button {
    background-color: #141414 !important;
    border: 1px solid #2e2e2e !important;
    border-radius: 8px !important;
    color: #e8e2d8 !important;
    transition: border-color 0.25s;
}
.stButton > button:hover { border-color: #d6c6a5 !important; }
.stExpander { border: 1px solid #222 !important; border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

st.title("🎬 AI Studio Elsewhere")
st.caption("云上电影工作室 · Beyond imagination, above the clouds — 云上。")

# ===========================================
# Sidebar Configuration
# ===========================================

st.sidebar.header("🎬 Film Projects")

# Storage status
if DATABASE_URL and not _db_error:
    st.sidebar.caption("💾 PostgreSQL connected")
elif DATABASE_URL and _db_error:
    st.sidebar.warning(f"⚠️ DB error: {_db_error}")
else:
    st.sidebar.warning("⚠️ DATABASE_URL not set — projects won't persist")

# Force refresh project list
if st.sidebar.button("🔄 Refresh Projects"):
    st.rerun()

_project_pairs = list_projects_with_titles()  # [(id, title), ...]
if _project_pairs:
    _project_ids    = [p[0] for p in _project_pairs]
    _project_labels = [p[1] for p in _project_pairs]
    active = st.session_state.get('active_project', _project_ids[0])
    default_idx = _project_ids.index(active) if active in _project_ids else 0
    _selected_label = st.sidebar.selectbox("Select a project", _project_labels, index=default_idx)
    selected_project = _project_ids[_project_labels.index(_selected_label)]
    st.session_state['active_project'] = selected_project
    st.sidebar.success(f"✅ {len(_project_pairs)} project(s) found")
else:
    selected_project = None
    st.sidebar.warning("No projects yet. Create one in the 'New Project' tab.")

st.sidebar.markdown("---")

# Subscription Info
st.sidebar.subheader("💳 Your Plan")
current_tier = subscription_manager.get_user_tier()
tier_info = subscription_manager.TIERS.get(current_tier, {})
st.sidebar.write(f"**{tier_info.get('name', 'Free')}** - {tier_info.get('price', '$0')}")

if current_tier == "free":
    if st.sidebar.button("🚀 Upgrade to Pro", use_container_width=True):
        email = st.session_state.user_email
        checkout_url = subscription_manager.get_checkout_url("pro", email)
        if checkout_url:
            st.sidebar.markdown(f"[💳 Go to Checkout]({checkout_url})")

st.sidebar.markdown("---")

# API Configuration
st.sidebar.header("🤖 AI Configuration")

st.sidebar.subheader("📝 Translation (OpenAI)")
openai_status = "✅ Configured" if os.getenv("OPENAI_API_KEY") else "⚠️ Not set"
st.sidebar.info(f"OpenAI API: {openai_status}")

st.sidebar.subheader("🎬 Cinematic Realism (Byteplus)")
byteplus_key = st.sidebar.text_input(
    "Byteplus API Key",
    type="password",
    value=os.getenv("BYTEPLUS_API_KEY", ""),
    help="ark-xxxx key from console.byteplus.com"
)
if byteplus_key:
    os.environ["BYTEPLUS_API_KEY"] = byteplus_key
    if not JIMENG_AVAILABLE:
        import jimeng_agent as _jimeng
        _jimeng.BYTEPLUS_API_KEY = byteplus_key
        _jimeng.AVAILABLE = True
    st.sidebar.success("✅ Byteplus Seedream configured")
elif openai_client:
    st.sidebar.info("🎬 Cinematic mode: DALL-E 3 (OpenAI) active")

st.sidebar.subheader("🎨 Concept Art (Wanxiang)")
dashscope_key = st.sidebar.text_input(
    "DashScope API Key",
    type="password",
    value=os.getenv("DASHSCOPE_API_KEY", ""),
    help="Get from https://dashscope.console.aliyun.com/"
)
if dashscope_key:
    os.environ["DASHSCOPE_API_KEY"] = dashscope_key
    st.sidebar.success("✅ Wanxiang configured")

st.sidebar.subheader("🎥 Video Generation (Runway)")
runway_key = st.sidebar.text_input(
    "Runway API Key",
    type="password",
    value=os.getenv("RUNWAY_API_KEY", ""),
    help="Get from https://runwayml.com/"
)
if runway_key:
    os.environ["RUNWAY_API_KEY"] = runway_key
    st.sidebar.success("✅ Runway configured")

st.sidebar.markdown("---")

# Data folders info
st.sidebar.write("📁 **Data Directories:**")
st.sidebar.code(
    f"Scripts:    {SCRIPTS_DIR}\n"
    f"Scenes:     {SCENES_DIR}\n"
    f"Concepts:   {CONCEPTS_DIR}\n"
    f"Videos:     {VIDEOS_DIR}\n"
    f"Exports:    {EXPORTS_DIR}",
    language=None
)

# ===========================================
# Main Navigation
# ===========================================

tab_home, tab_new_project, tab_script, tab_scenes, tab_concepts, tab_video, tab_characters, tab_storyboard, tab_locations, tab_exports = st.tabs([
    "🏠 Home",
    "📝 New Project",
    "📄 Script Upload",
    "🎬 Scene Breakdown",
    "🎨 Concept Images",
    "🎥 Video Generation",
    "🎭 Characters",
    "📋 Storyboard",
    "📍 Locations",
    "📦 Export"
])

# ===========================================
# Tab: Home
# ===========================================

with tab_home:
    
    # Hero Section
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0;">
        <h1 style="font-size: 2.2rem; margin-bottom: 0.3rem;">AI Studio Elsewhere</h1>
        <h3 style="font-weight: 400; opacity: 0.8;">云上电影工作室</h3>
        <p style="font-size: 1.15rem; opacity: 0.7; max-width: 600px; margin: 0.8rem auto;">
            From script to screen — before you spend a single dollar on production.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # What You Can Do — director-focused
    st.markdown("### What can you do here?")
    st.markdown("")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### 🌐 Translate Everything — Chinese ↔ English")
        st.markdown("Upload a script in Chinese and get a full English translation — scenes, dialogue, loglines, story notes. Or go the other way. Pinyin included. Your film crosses borders before it even wraps.")
        st.markdown("")
        
        st.markdown("##### 🎨 See Your Film Before You Shoot It")
        st.markdown("Generate concept art for every scene. Choose cinematic, surreal, noir, or documentary styles. Each image is crafted from your script's mood, location, and action.")
        st.markdown("")
        
        st.markdown("##### 🎥 Generate Experimental Video")
        st.markdown("Turn your concept art into short video clips with camera motion — dolly, pan, orbit, tilt. Preview how scenes feel in motion before you commit to a shoot.")
    
    with col2:
        st.markdown("##### 📄 Upload Any Script, Any Language")
        st.markdown("Drop in a PDF, Word doc, or plain text — in Chinese or English. The system extracts every scene, translates, and organizes your story automatically.")
        st.markdown("")
        
        st.markdown("##### 🎬 Break Down Every Scene")
        st.markdown("AI reads your script and identifies locations, characters, time of day, mood, and key actions. No manual work — just upload and go.")
        st.markdown("")
        
        st.markdown("##### 📍 Scout Real Locations")
        st.markdown("Search Google Places for real-world filming locations that match your scenes. See photos, ratings, and addresses — all from inside the studio.")
        st.markdown("")
        
        st.markdown("##### 📋 Build Your Storyboard")
        st.markdown("Assemble 6, 8, or 12-panel storyboards from your scenes. Export as PDF — ready for your crew, your investors, or your own creative process.")
    
    st.markdown("---")
    
    # The Workflow
    st.markdown("### Your workflow")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("**Step 1**")
        st.markdown("📝 Create a project and upload your script")
    with col2:
        st.markdown("**Step 2**")
        st.markdown("🎬 Review your scene breakdown — edit, refine")
    with col3:
        st.markdown("**Step 3**")
        st.markdown("🎨 Generate concept art and video experiments")
    with col4:
        st.markdown("**Step 4**")
        st.markdown("📦 Export your director's package — PDF, images, storyboard")
    
    st.markdown("---")
    
    # Built For
    st.markdown("### Built for directors who think visually — and work across languages")
    st.markdown("""
    This is not post-production software. This is a **pre-production imagination engine**.
    
    Use it to explore your film before cameras roll. Test moods. Try locations. 
    See what your story looks like — then decide what to shoot.
    
    **Translation is at the core.** Upload a script in Mandarin, get a complete English 
    translation — every scene, every line of dialogue, every logline. Or start in English 
    and translate to Chinese. The system handles OCR, segmentation, and Pinyin automatically.
    
    Built for international co-productions, festival submissions, and cross-cultural storytelling.
    """)
    
    st.markdown("---")
    
    # Current Projects
    st.markdown("### Your Projects")
    
    if _project_pairs:
        for proj_id, proj_title in _project_pairs[:5]:
            proj = load_project(proj_id)
            if proj:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(f"**{proj.title_en}** {f'({proj.title_zh})' if proj.title_zh else ''}")
                with col2:
                    st.markdown(f"🎬 {len(proj.scenes)} scenes")
                with col3:
                    st.markdown(f"👤 {proj.director}")
    else:
        st.info("No projects yet. Create one in the **New Project** tab, or try the demo below.")
    
    # Demo Project Loader
    if DEMO_AVAILABLE:
        st.markdown("---")
        st.markdown("### 🎬 Try it now")
        st.markdown("Load **The Last Night Tram** (夜晚最后一班电车) — a complete demo film project with 3 scenes, moods, and visual prompts. No script upload needed.")
        if st.button("🚀 Load Demo Project", type="primary", use_container_width=True, key="load_demo"):
            demo = load_demo_project()
            project_id = "the_last_night_tram"
            
            # Convert demo scenes to SceneBreakdown objects
            demo_scenes = []
            for s in demo["scenes"]:
                demo_scenes.append(SceneBreakdown(
                    scene_id=f"scene_{s['id']}",
                    scene_number=s["number"],
                    heading=s["title"],
                    location=s["location"],
                    time_of_day="Night",
                    characters=[],
                    action=s["text_en"],
                    dialogue=[],
                    mood=", ".join(s["mood"]) if isinstance(s["mood"], list) else s["mood"],
                    keywords=s["mood"] if isinstance(s["mood"], list) else []
                ))
            
            project = Project(
                project_id=project_id,
                title_en=demo["title"],
                title_zh=demo["title_zh"],
                director=demo["director"],
                logline=demo["logline_en"],
                created_at=datetime.now().isoformat(),
                last_updated=datetime.now().isoformat(),
                script_path=None,
                scenes=demo_scenes
            )
            save_project(project)
            st.balloons()
            st.success("✅ Demo project loaded: **The Last Night Tram** (夜晚最后一班电车)")
            st.info("Select it from the sidebar dropdown, then explore all tabs!")

# ===========================================
# Tab: New Project
# ===========================================

with tab_new_project:
    st.subheader("📝 Create a New Film Project")
    
    col1, col2 = st.columns(2)
    
    with col1:
        title_en = st.text_input("Film Title (English)")
        director = st.text_input("Director Name")
    
    with col2:
        title_zh = st.text_input("Film Title (Chinese) 中文")
        logline = st.text_area("Logline (1-2 sentences)")
    
    if st.button("🎬 Create Project", type="primary", use_container_width=True):
        if not title_en or not director:
            st.error("❌ Title and director required")
        else:
            project_id = title_en.lower().replace(" ", "_")
            project = Project(
                project_id=project_id,
                title_en=title_en,
                title_zh=title_zh or None,
                director=director,
                logline=logline,
                created_at=datetime.now().isoformat(),
                last_updated=datetime.now().isoformat(),
                script_path=None
            )
            save_project(project)
            st.session_state['active_project'] = project_id
            st.balloons()
            st.success(f"✅ Project created: {title_en}")
            st.rerun()

# ===========================================
# Tab: Script Upload
# ===========================================

with tab_script:
    st.subheader("📄 Upload Script")
    
    if not selected_project:
        st.warning("⚠️ Select or create a project first")
    else:
        project = load_project(selected_project)
        
        st.markdown(f"### {project.title_en} ({project.title_zh})")
        
        st.markdown("""
        Upload your film script in any format:
        - 📄 PDF
        - 📝 Word (.docx)
        - 📋 Plain text (.txt)
        - 🎞️ Images (storyboard photos)
        """)
        
        uploaded_file = st.file_uploader(
            "Choose a script file",
            type=["pdf", "docx", "txt", "png", "jpg", "jpeg"]
        )
        
        if uploaded_file:
            st.write(f"**File:** {uploaded_file.name}")

            # Read bytes once — used for both save and extraction
            file_bytes = uploaded_file.read()

            # Save uploaded file
            script_path = SCRIPTS_DIR / f"{selected_project}_script_{uploaded_file.name}"
            with open(script_path, "wb") as f:
                f.write(file_bytes)

            st.success(f"✅ File saved: {uploaded_file.name}")

            # Extract text based on file type
            extracted_text = ""

            if uploaded_file.type == "application/pdf":
                if PYMUPDF_AVAILABLE:
                    # Staged extraction — user chooses how much to process
                    extraction_mode = st.radio(
                        "How much of the script to extract?",
                        options=["Quick preview (first 3 pages)", "Default (first 10 pages)", "Full script (all pages — slower)"],
                        index=1,
                        horizontal=True,
                        key="extract_mode",
                    )
                    if extraction_mode.startswith("Quick"):
                        pages_limit = 3
                    elif extraction_mode.startswith("Full"):
                        pages_limit = 9999
                        st.warning("⚠️ Full extraction may take 10–30s for long scripts. AI scene parsing will also take longer.")
                    else:
                        pages_limit = MAX_PAGES

                    if st.button("Extract Text", key="do_extract"):
                        progress = st.progress(0)
                        try:
                            doc = fitz.open(stream=file_bytes, filetype="pdf")
                            total = min(len(doc), pages_limit)
                            pages_text = []
                            for i, page in enumerate(doc):
                                if i >= pages_limit:
                                    break
                                page_text = page.get_text()
                                if page_text.strip():
                                    pages_text.append(page_text)
                                progress.progress((i + 1) / max(total, 1))
                            extracted_text = "\n".join(pages_text)
                            progress.empty()
                            st.session_state[f"extracted_{selected_project}"] = extracted_text
                        except Exception as e:
                            st.error(f"❌ PDF extraction failed: {e}")
                    # Use previously extracted text if available
                    if not extracted_text:
                        extracted_text = st.session_state.get(f"extracted_{selected_project}", "")
                else:
                    # Legacy fallback — slow OCR path
                    st.info("📄 Processing PDF (slow path — install pymupdf for speed)...")
                    images, page_paths = extract_pages_from_pdf(str(script_path))
                    if images:
                        st.write(f"Extracted {len(images)} pages")
                        if page_paths:
                            all_text = []
                            for page_path in page_paths:
                                text = extract_text_from_image(page_path)
                                if text:
                                    all_text.append(text)
                            extracted_text = "\n".join(all_text)

            elif uploaded_file.type == "text/plain":
                extracted_text = file_bytes.decode("utf-8")
            
            if extracted_text:
                st.write(f"**Total extracted: {len(extracted_text)} characters**")
                
                with st.expander("View extracted text"):
                    st.text(extracted_text[:1000])
                
                # Save to project
                project.script_path = str(script_path)
                save_project(project)

# ===========================================
# Tab: Scene Breakdown
# ===========================================

with tab_scenes:
    st.subheader("🎬 Scene Breakdown & Analysis")
    
    if not selected_project:
        st.warning("⚠️ Select a project first")
    else:
        project = load_project(selected_project)
        
        if not project.script_path and not project.scenes:
            st.warning("⚠️ Upload a script first in the 'Script Upload' tab")
        else:
            st.markdown(f"### {project.title_en}")
            
            if project.script_path:
                if st.button("🔍 Analyze Script → Extract Scenes", type="primary", use_container_width=True):
                    script_path = Path(project.script_path)
                    script_text = ""

                    # Step 1: fast text extraction
                    if script_path.suffix == ".pdf" and PYMUPDF_AVAILABLE:
                        with st.spinner("Extracting script text..."):
                            script_text = extract_text_fast(script_path.read_bytes())
                    elif script_path.suffix == ".pdf":
                        images, page_paths = extract_pages_from_pdf(str(script_path))
                        for page_path in page_paths:
                            script_text += extract_text_from_image(page_path) + "\n"
                    elif script_path.suffix == ".txt":
                        script_text = script_path.read_text(encoding="utf-8")

                    if script_text:
                        preview_slot = None
                        quick_scenes = list(stream_scenes_from_text(script_text))
                        if quick_scenes:
                            st.markdown("*Scene structure detected — enriching with AI...*")
                            preview_slot = st.empty()
                            with preview_slot.container():
                                for qs in quick_scenes[:5]:
                                    st.caption(f"🎬 {qs['heading']}")

                        # Step 3: full GPT enrichment
                        with st.spinner("Extracting scenes..."):
                            scenes = parse_script_to_scenes(script_text)
                            project.scenes = scenes
                            save_project(project)
                        if preview_slot:
                            preview_slot.empty()
                        st.success(f"✅ {len(scenes)} scenes extracted")
                    else:
                        st.error("❌ Could not extract text from script")
            elif project.scenes:
                st.success(f"✅ {len(project.scenes)} scenes pre-loaded (demo project)")
            
            # Display scenes
            if project.scenes:
                # ── Director Insights Dashboard ───────────────────────────────
                insights = build_director_insights(project.scenes)
                if insights:
                    st.markdown("#### Director Insights")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Scenes", insights['total'])
                    c2.metric("Pacing", insights['pacing'].title())
                    c3.metric("Dominant", insights['dominant'])
                    c4.metric("Weak scenes", insights['weak'])
                    st.progress(insights['strength'], text=f"Script strength: {int(insights['strength']*100)}%")
                    # Classification breakdown
                    if insights['counts']:
                        breakdown = "  ·  ".join(f"{k}: {v}" for k, v in sorted(insights['counts'].items(), key=lambda x: -x[1]))
                        st.caption(breakdown)
                    st.markdown("---")

                st.write(f"**{len(project.scenes)} scenes**")

                for i, scene in enumerate(project.scenes):
                    # Ensure classification is set (handles scenes loaded from disk before this feature)
                    if not getattr(scene, 'classification', ''):
                        scene.classification = classify_scene(scene)
                    prompts = build_scene_prompts(scene)
                    issues  = detect_weak_scene(scene)
                    stype   = prompts.get('scene_type', 'STANDARD')

                    type_colors = {'INTERCUT': '#ffcc00', 'FLASHBACK': '#66ccff',
                                   'MONTAGE': '#ff6699', 'STANDARD': '#666666'}
                    cls_colors  = {'ACTION': '#ff6644', 'DIALOGUE': '#66aaff',
                                   'ATMOSPHERIC': '#aaaaaa', 'EMOTIONAL': '#cc88ff',
                                   'TRANSITION': '#ffcc44', 'EXPOSITION': '#88ccaa'}

                    label = f"Scene {scene.scene_number}: {scene.heading}"
                    if issues:
                        label += "  ⚠️"

                    with st.expander(label):
                        # Badges row
                        badges = []
                        if stype != 'STANDARD':
                            tc = type_colors.get(stype, '#666')
                            badges.append(f'<span style="background:{tc};color:#000;padding:2px 8px;border-radius:3px;font-size:0.7rem;font-weight:700">{stype}</span>')
                        cc = cls_colors.get(scene.classification, '#aaa')
                        badges.append(f'<span style="background:{cc};color:#000;padding:2px 8px;border-radius:3px;font-size:0.7rem;font-weight:700">{scene.classification}</span>')
                        if badges:
                            st.markdown(' &nbsp; '.join(badges), unsafe_allow_html=True)
                            st.write('')

                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Location:** {scene.location or prompts['location']}")
                            st.write(f"**Time:** {scene.time_of_day}")
                            st.write(f"**Mood:** {scene.mood or ', '.join(prompts['mood'])}")
                        with col2:
                            st.write(f"**Characters:** {', '.join(scene.characters) or 'None'}")
                            st.write(f"**Keywords:** {', '.join(scene.keywords)}")
                            st.caption(f"Camera: {prompts['camera']}")

                        st.write("**Action:**")
                        st.write(scene.action)

                        if issues:
                            st.warning(f"Script doctor: {' · '.join(issues)}")

                        # Shot list
                        with st.expander("Shot list", expanded=False):
                            shot_options = generate_shot_list(scene.classification)
                            selected_shot = st.radio(
                                "Select shot to queue for video:",
                                shot_options,
                                key=f"shotlist_{i}",
                                label_visibility="collapsed",
                            )
                            if st.button("→ Queue this shot for video", key=f"qshot_{i}"):
                                st.session_state[f"queued_shot_{scene.scene_id}"] = selected_shot
                                st.success(f"Queued: {selected_shot}")

                        # Cinematic prompts
                        with st.expander("Cinematic prompts", expanded=False):
                            st.text_area("Visual prompt", prompts['visual_prompt'], height=68,
                                         key=f"vp_{i}", label_visibility="visible")
                            st.text_area("Video prompt", prompts['video_prompt'], height=68,
                                         key=f"vvp_{i}", label_visibility="visible")

                        # AI rewrite
                        with st.expander("Rewrite with AI", expanded=False):
                            if not openai_client:
                                st.warning(f"OpenAI unavailable: {_openai_init_error or 'unknown error'}")
                            else:
                                style_choice = st.selectbox(
                                    "Style",
                                    options=list(_REWRITE_STYLES.keys()),
                                    key=f"rwstyle_{i}"
                                )
                                rw_key = f"rw_result_{scene.scene_id}"
                                if st.button("Rewrite scene", key=f"rw_{i}"):
                                    with st.spinner("Rewriting..."):
                                        st.session_state[rw_key] = rewrite_scene_ai(scene.action, style_choice)
                                if st.session_state.get(rw_key):
                                    rewritten = st.session_state[rw_key]
                                    col_orig, col_new = st.columns(2)
                                    with col_orig:
                                        st.caption("Original")
                                        st.write(scene.action[:600])
                                    with col_new:
                                        st.caption(f"{style_choice}")
                                        st.write(rewritten)
                                    if st.button("✅ Apply this rewrite", key=f"rw_apply_{i}"):
                                        scene.action = rewritten
                                        del st.session_state[rw_key]
                                        save_project(project)
                                        st.success("Rewrite saved.")
                                        st.rerun()

# ===========================================
# Tab: Concept Images
# ===========================================

with tab_concepts:
    st.subheader("🎨 Generate Concept Images")

    with st.expander("🔍 Provider Status", expanded=False):
        st.json({
            "openai_client": "✅ ready" if openai_client else f"❌ None — {_openai_init_error}",
            "OPENAI_API_KEY": "set" if os.getenv("OPENAI_API_KEY") else "MISSING",
            "BYTEPLUS_API_KEY": "set" if os.getenv("BYTEPLUS_API_KEY") else "MISSING",
            "JIMENG_AVAILABLE": JIMENG_AVAILABLE,
            "WANX_AVAILABLE": WANX_AVAILABLE,
            "DASHSCOPE_API_KEY": "set" if os.getenv("DASHSCOPE_API_KEY") else "MISSING",
        })
    
    # Check subscription
    if not subscription_manager.has_feature("concept_images") and not st.session_state.get("is_admin", False):
        st.error("🔒 Concept Image Generation - Pro Plan Required")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Plan", subscription_manager.get_user_tier().title())
        with col2:
            st.metric("Required Plan", "Pro or Studio")
        with col3:
            if st.button("💳 Upgrade to Pro", use_container_width=True):
                email = st.session_state.user_email
                checkout_url = subscription_manager.get_checkout_url("pro", email)
                if checkout_url:
                    st.markdown(f"[💳 Checkout]({checkout_url})")
        
        st.write("---")
        st.write("**Pro Plan ($9.99/month) includes:**")
        st.write("✅ Concept Image Generation")
        st.write("✅ Video Generation (Runway)")
        st.write("✅ Export & Download")
    
    elif not selected_project:
        st.warning("⚠️ Select a project first")
    else:
        # Force reload project to get latest scenes
        project = load_project(selected_project)
        
        if not project.scenes:
            st.warning("⚠️ Extract scenes first (Scene Breakdown tab)")
        else:
            st.markdown(f"### {project.title_en}")

            # ── Controls row ─────────────────────────────────────────
            c1, c2, c3 = st.columns(3)
            with c1:
                visual_direction = st.selectbox(
                    "🎬 Visual Direction",
                    ["Natural Realism", "Noir B&W", "Dreamlike",
                     "Gritty Realism", "Period Film (1940s)", "Poetic Cinema"],
                )
            with c2:
                output_type = st.selectbox(
                    "🎯 Output Type",
                    ["Cinematic Frame (for video)", "Storyboard Frame",
                     "Reference Photography", "Mood Exploration"],
                )
            with c3:
                video_ready = st.checkbox("🎥 Optimize for Video Generation", value=True,
                    help="Enforces photorealism and natural motion potential — ensures Runway behaves correctly")

            # ── Generation Mode ───────────────────────────────────────
            col_mode, col_info = st.columns([2, 3])
            with col_mode:
                image_mode = st.radio(
                    "Generation Mode",
                    ["🎬 Cinematic Realism", "🎨 Concept Art"],
                    horizontal=True,
                )
            with col_info:
                if "Cinematic" in image_mode:
                    if openai_client:
                        st.success("🎬 Cinematic mode: DALL-E 3 / gpt-image-1 — photorealistic output")
                    elif JIMENG_AVAILABLE:
                        st.success("✅ Byteplus Seedream connected — photorealistic output")
                    else:
                        st.warning("⚠️ Add OPENAI_API_KEY or BYTEPLUS_API_KEY")
                else:
                    st.info("🎨 Wanxiang — illustrated concept art style")

            image_gen_mode = "cinematic" if "Cinematic" in image_mode else "concept"

            # ── Scene selection ───────────────────────────────────────
            scene_options = {f"Scene {s.scene_number}: {s.heading}": i for i, s in enumerate(project.scenes)}
            selected_scenes = st.multiselect("Select scenes", list(scene_options.keys()))

            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                do_generate = st.button("🎨 Generate", type="primary", use_container_width=True)
            with btn_col2:
                do_compare = st.button("⚡ Compare Both Models", use_container_width=True,
                    help="Generate the same scene with Concept Art AND Cinematic Realism side by side")

            # ── Helpers ───────────────────────────────────────────────
            def _render_concept_card(img_path: str, scene, key_suffix: str):
                try:
                    st.image(img_path, use_container_width=True)
                except Exception:
                    st.write(f"[Image]({img_path})")
                p = Path(img_path)
                a1, a2, a3 = st.columns(3)
                with a1:
                    if p.exists():
                        st.download_button("⬇ Save", data=p.read_bytes(),
                            file_name=p.name, mime="image/png", key=f"dl_{key_suffix}")
                with a2:
                    if st.button("🎬 Use as Video Base", key=f"vb_{key_suffix}"):
                        st.session_state["video_base_scene_id"] = scene.scene_id
                        st.session_state["video_base_image_path"] = img_path
                        st.success("✅ Set as video base — go to Video Generation tab")
                with a3:
                    if st.button("↺ Regenerate", key=f"regen_{key_suffix}"):
                        st.session_state[f"regen_{scene.scene_id}"] = True
                        st.rerun()

            # ── Generate ──────────────────────────────────────────────
            if (do_generate or do_compare) and not selected_scenes:
                st.warning("⚠️ Select at least one scene")

            if do_generate and selected_scenes:
                for scene_label in selected_scenes:
                    scene = project.scenes[scene_options[scene_label]]
                    st.markdown(f"#### 🎬 {scene.heading}")
                    with st.spinner(f"Generating..."):
                        images = generate_concept_images(
                            scene, visual_direction.lower(),
                            project_id=project.project_id,
                            mode=image_gen_mode,
                            output_type=output_type,
                            video_ready=video_ready,
                        )
                    if images:
                        project.concepts[scene.scene_id] = images
                        save_project(project)
                        for j, img_path in enumerate(images[:4]):
                            _render_concept_card(img_path, scene, f"gen_{scene.scene_id}_{j}")

            if do_compare and selected_scenes:
                for scene_label in selected_scenes:
                    scene = project.scenes[scene_options[scene_label]]
                    st.markdown(f"#### ⚡ {scene.heading} — Model Comparison")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**🎨 Concept Art** *(Wanxiang — illustrated)*")
                        with st.spinner("Concept Art..."):
                            imgs_concept = generate_concept_images(
                                scene, visual_direction.lower(),
                                project_id=project.project_id, mode="concept",
                                output_type=output_type, video_ready=False,
                            )
                        if imgs_concept:
                            _render_concept_card(imgs_concept[0], scene, f"cmp_concept_{scene.scene_id}")
                    with col_b:
                        st.markdown("**🎬 Cinematic Realism** *(photorealistic — video-ready)*")
                        with st.spinner("Cinematic Realism..."):
                            imgs_cine = generate_concept_images(
                                scene, visual_direction.lower(),
                                project_id=project.project_id, mode="cinematic",
                                output_type=output_type, video_ready=True,
                            )
                        if imgs_cine:
                            st.success("🎥 Best for video generation")
                            _render_concept_card(imgs_cine[0], scene, f"cmp_cine_{scene.scene_id}")
                    # Save cinematic as primary if generated
                    best = imgs_cine or imgs_concept
                    if best:
                        project.concepts[scene.scene_id] = best
                        save_project(project)

            # ── Previously generated ──────────────────────────────────
            if project.concepts:
                st.markdown("---")
                st.markdown("#### Previously Generated Concepts")
                for scene in project.scenes:
                    paths = project.concepts.get(scene.scene_id, [])
                    if not paths:
                        continue
                    st.markdown(f"**🎬 {scene.heading}**")
                    cols = st.columns(min(len(paths), 3))
                    for j, img_path in enumerate(paths[:3]):
                        with cols[j]:
                            _render_concept_card(img_path, scene, f"saved_{scene.scene_id}_{j}")

# ===========================================
# Tab: Video Generation
# ===========================================

with tab_video:
    st.subheader("🎥 Generate Experimental Videos")
    
    # Check subscription
    if not subscription_manager.has_feature("video_generation") and not st.session_state.get("is_admin", False):
        st.error("🔒 Video Generation - Pro Plan Required")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Plan", subscription_manager.get_user_tier().title())
        with col2:
            st.metric("Required Plan", "Pro or Studio")
        with col3:
            if st.button("💳 Upgrade to Pro", use_container_width=True, key="video_upgrade"):
                email = st.session_state.user_email
                checkout_url = subscription_manager.get_checkout_url("pro", email)
                if checkout_url:
                    st.markdown(f"[💳 Checkout]({checkout_url})")
        
        st.write("---")
        st.write("**Pro Plan ($9.99/month) includes:**")
        st.write("✅ Video Generation (Runway Gen-4.5)")
        st.write("✅ 100 API calls/month")
        st.write("✅ Export & Download")
        st.write("")
        st.write("**Studio Plan ($49.99/month) includes:**")
        st.write("✅ Everything in Pro")
        st.write("✅ Batch Processing")
        st.write("✅ 1000 API calls/month")
    
    elif not selected_project:
        st.warning("⚠️ Select a project first")
    else:
        # Force reload project to get latest scenes
        project = load_project(selected_project)
        
        st.markdown(f"### {project.title_en}")
        
        if not project.scenes:
            st.warning("⚠️ Extract scenes first (Scene Breakdown tab)")
        else:
            # Convert scenes to format for video generation
            def _concept_for_runway(scene_id: str) -> Optional[str]:
                """Return concept image as local path (display) or base64 data URI (Runway API)."""
                paths = project.concepts.get(scene_id, [])
                if not paths:
                    return None
                path = paths[0]
                p = Path(path)
                if p.exists():
                    import base64
                    data = base64.b64encode(p.read_bytes()).decode()
                    return f"data:image/png;base64,{data}"
                return path  # fall back to URL if local file missing

            scenes_for_video = [
                {
                    "id": scene.scene_id,
                    "heading": scene.heading,
                    "prompt": f"{scene.heading}. Location: {scene.location}. Time: {scene.time_of_day}. Mood: {scene.mood}. Action: {scene.action[:100]}",
                    "concept_image": _concept_for_runway(scene.scene_id),
                    "concept_image_path": (project.concepts.get(scene.scene_id) or [None])[0],
                }
                for scene in project.scenes
            ]
            
            try:
                from runway_video_ui import display_video_generation_tab
                display_video_generation_tab(scenes_for_video, project.title_en)
            except Exception as _video_err:
                st.error(f"⚠️ Video module error: {_video_err}")
                st.markdown("---")
                
                # Demo fallback: let directors preview workflow without API
                st.markdown("#### 🎬 Video Generation Preview (Demo Mode)")
                st.info("This demo shows the video generation workflow. Connect Runway API keys to generate real videos.")
                
                # Scene selector
                scene_names = [s["heading"] for s in scenes_for_video]
                selected_scene = st.selectbox("🎬 Select Scene", scene_names, key="demo_video_scene")
                scene_data = scenes_for_video[scene_names.index(selected_scene)]
                
                col1, col2 = st.columns(2)
                with col1:
                    shot_type = st.selectbox("📹 Shot Type", [
                        "Wide Shot", "Medium Shot", "Close-Up", 
                        "Dolly In", "Pan Left", "Orbit", "Push In"
                    ], key="demo_shot_type")
                with col2:
                    duration = st.slider("⏱️ Duration (seconds)", 3, 15, 5, key="demo_duration")
                
                st.text_area("🎯 Scene Prompt", scene_data["prompt"], height=80, key="demo_prompt")
                
                if st.button("🎥 Generate Demo Video", type="primary", use_container_width=True, key="demo_gen"):
                    with st.spinner("🎬 Generating preview..."):
                        import time
                        progress = st.progress(0)
                        for i in range(100):
                            time.sleep(0.02)
                            progress.progress(i + 1)
                        
                        st.success("✅ Demo video generated!")
                        st.markdown(f"""
                        **Scene:** {selected_scene}  
                        **Shot:** {shot_type}  
                        **Duration:** {duration}s  
                        
                        🎬 *In production mode, Runway Gen-4.5 would generate a cinematic video clip here.*  
                        *To enable: add `RUNWAY_API_KEY` to your Railway environment variables.*
                        """)
                        
                        # Show a placeholder with scene info
                        st.markdown("---")
                        st.markdown("##### 📋 Shot List Generated")
                        for i, s in enumerate(scenes_for_video[:5], 1):
                            st.write(f"**Shot {i}:** {s['heading']}")

# ===========================================
# Tab: Characters (GWM-1 Avatars)
# ===========================================

with tab_characters:
    if not CHARACTERS_AVAILABLE:
        st.subheader("🎭 Character Bible (Demo Mode)")
        st.info("Connect Runway Characters module for AI avatar generation. Showing character planning tools.")
        
        if not selected_project:
            st.warning("⚠️ Select a project first")
        else:
            project = load_project(selected_project)
            
            # Character planning even without Runway
            st.markdown("#### 📝 Character Profiles")
            
            char_name = st.text_input("Character Name", key="demo_char_name")
            char_role = st.selectbox("Role", ["Protagonist", "Antagonist", "Supporting", "Minor"], key="demo_char_role")
            char_desc = st.text_area("Description", placeholder="Physical appearance, personality, motivation...", key="demo_char_desc")
            
            col1, col2 = st.columns(2)
            with col1:
                char_age = st.text_input("Age", key="demo_char_age")
            with col2:
                char_trait = st.text_input("Key Trait", key="demo_char_trait")
            
            if st.button("💾 Save Character Profile", type="primary", key="demo_save_char"):
                if char_name:
                    st.success(f"✅ Character '{char_name}' saved to project")
                else:
                    st.warning("Enter a character name")
            
            # Show existing characters from scenes
            if project.scenes:
                st.markdown("---")
                st.markdown("#### 🎬 Characters Found in Script")
                all_chars = set()
                for scene in project.scenes:
                    all_chars.update(scene.characters)
                if all_chars:
                    for char in sorted(all_chars):
                        st.write(f"• **{char}**")
                else:
                    st.write("No characters extracted yet. Run Scene Breakdown first.")
    else:
        # Character creation and management
        char_tab1, char_tab2 = st.tabs(["Create Character", "Manage Characters"])
        
        with char_tab1:
            display_character_creation_tab()
        
        with char_tab2:
            display_character_management()

# Tab: Storyboard
# ===========================================

with tab_storyboard:
    st.subheader("📋 Storyboard Assembly")
    
    if not selected_project:
        st.warning("⚠️ Select a project first")
    else:
        project = load_project(selected_project)
        
        st.markdown(f"### {project.title_en}")
        
        if not project.scenes:
            st.warning("⚠️ Extract scenes first (Scene Breakdown tab)")
        else:
            # Scene selector
            scene_options = {f"Scene {s.scene_number}: {s.heading}": i for i, s in enumerate(project.scenes)}
            selected_scene_name = st.selectbox("🎬 Select Scene", list(scene_options.keys()), key="storyboard_scene")
            scene_idx = scene_options[selected_scene_name]
            scene = project.scenes[scene_idx]
            
            # Build scene dict for storyboard generator
            scene_dict = {
                "scene_number": scene.scene_number,
                "heading": scene.heading,
                "location": scene.location,
                "time_of_day": scene.time_of_day,
                "characters": scene.characters,
                "mood": scene.mood,
                "action": scene.action,
                "visual_prompt": f"{scene.heading}. {scene.location}, {scene.time_of_day}. Mood: {scene.mood}. {scene.action[:200]}",
                "video_prompt": f"Cinematic scene: {scene.heading}, {scene.mood} atmosphere"
            }
            
            try:
                display_storyboard_ui(
                    scene=scene_dict,
                    generate_image_func=None,
                    title="🎬 Storyboard Builder"
                )
            except Exception as e:
                st.error(f"Storyboard module error: {e}")
                st.info("Falling back to basic storyboard view...")
                
                layout = st.selectbox("Choose layout", ["6-panel", "8-panel", "12-panel scroll"])
                st.info(f"📋 Assembling storyboard with {layout} layout...")
            
            # PDF Export
            st.markdown("---")
            st.markdown("#### 📄 Export Storyboard PDF")
            try:
                settings = create_pdf_export_settings()
                if st.button("📥 Export Storyboard PDF", type="primary", key="export_storyboard_pdf"):
                    display_pdf_export_ui(project, settings)
            except Exception as e:
                st.info(f"PDF export not available: {e}")

# ===========================================
# Tab: Locations
# ===========================================

with tab_locations:
    st.subheader("📍 Location Scouting")
    
    if not selected_project:
        st.warning("⚠️ Select a project first")
    else:
        project = load_project(selected_project)
        
        if not PLACES_AVAILABLE:
            st.error("❌ Google Places module not available")
        else:
            google_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
            
            if not google_api_key:
                st.warning("⚠️ Google Places API key not configured")
                google_api_key = st.text_input("Enter Google Places API Key", type="password", key="gplaces_key")
                if google_api_key:
                    os.environ["GOOGLE_PLACES_API_KEY"] = google_api_key
            
            if google_api_key:
                agent = GooglePlacesAgent(google_api_key)
                
                st.markdown(f"### {project.title_en}")
                
                # Two modes: search from scenes or free search
                location_mode = st.radio(
                    "Search mode",
                    ["🎬 From Scene Locations", "🔍 Free Search"],
                    horizontal=True,
                    key="loc_mode"
                )
                
                if location_mode == "🎬 From Scene Locations" and project.scenes:
                    st.markdown("---")
                    st.markdown("Select a scene to find real-world filming locations that match:")
                    
                    scene_options = {
                        f"Scene {s.scene_number}: {s.heading} — 📍 {s.location}": i 
                        for i, s in enumerate(project.scenes)
                    }
                    selected_scene_name = st.selectbox(
                        "🎬 Select Scene", 
                        list(scene_options.keys()), 
                        key="loc_scene_select"
                    )
                    scene_idx = scene_options[selected_scene_name]
                    scene = project.scenes[scene_idx]
                    
                    # Show scene info
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**Location:** {scene.location}")
                    with col2:
                        st.markdown(f"**Time:** {scene.time_of_day}")
                    with col3:
                        st.markdown(f"**Mood:** {scene.mood}")
                    
                    # Allow editing the search query
                    search_query = st.text_input(
                        "🔍 Search query (edit to refine)",
                        value=f"{scene.location} filming location",
                        key="loc_scene_query"
                    )
                    
                    if st.button("🌍 Scout Locations", type="primary", use_container_width=True, key="loc_scout_btn"):
                        with st.spinner("🔍 Searching for locations..."):
                            results = agent.search_locations(search_query, max_results=6)
                            
                            if results:
                                st.success(f"✅ Found {len(results)} locations")
                                
                                for i, loc in enumerate(results):
                                    with st.expander(f"📍 {loc['name']} — ⭐ {loc.get('rating', 'N/A')}"):
                                        st.markdown(f"**Address:** {loc['address']}")
                                        
                                        if loc.get('rating'):
                                            st.markdown(f"**Rating:** ⭐ {loc['rating']} ({loc.get('user_ratings_total', 0)} reviews)")
                                        
                                        st.markdown(f"**Coordinates:** {loc['lat']:.4f}, {loc['lng']:.4f}")
                                        
                                        # Show photos
                                        if loc.get("photo_refs"):
                                            photo_cols = st.columns(min(len(loc["photo_refs"]), 3))
                                            for j, ref in enumerate(loc["photo_refs"][:3]):
                                                photo_url = agent.get_photo_url(ref)
                                                if photo_url:
                                                    with photo_cols[j]:
                                                        st.image(photo_url, use_container_width=True)
                                        
                                        # Google Maps link
                                        maps_url = f"https://www.google.com/maps/place/?q=place_id:{loc['place_id']}"
                                        st.markdown(f"[🗺️ Open in Google Maps]({maps_url})")
                            else:
                                st.warning("No locations found. Try a different search query.")
                
                elif location_mode == "🎬 From Scene Locations" and not project.scenes:
                    st.info("Load scenes first (Scene Breakdown tab) to search by scene location.")
                
                else:
                    # Free search mode
                    st.markdown("---")
                    st.markdown("Search for any filming location worldwide:")
                    
                    search_query = st.text_input(
                        "🔍 Search",
                        placeholder="e.g., abandoned tram station Europe, neon alley Tokyo, misty mountain village",
                        key="loc_free_query"
                    )
                    
                    if search_query and st.button("🌍 Search", type="primary", use_container_width=True, key="loc_free_btn"):
                        with st.spinner("🔍 Searching..."):
                            results = agent.search_locations(search_query, max_results=6)
                            
                            if results:
                                st.success(f"✅ Found {len(results)} locations")
                                
                                for i, loc in enumerate(results):
                                    with st.expander(f"📍 {loc['name']} — ⭐ {loc.get('rating', 'N/A')}"):
                                        st.markdown(f"**Address:** {loc['address']}")
                                        
                                        if loc.get('rating'):
                                            st.markdown(f"**Rating:** ⭐ {loc['rating']} ({loc.get('user_ratings_total', 0)} reviews)")
                                        
                                        st.markdown(f"**Coordinates:** {loc['lat']:.4f}, {loc['lng']:.4f}")
                                        
                                        if loc.get("photo_refs"):
                                            photo_cols = st.columns(min(len(loc["photo_refs"]), 3))
                                            for j, ref in enumerate(loc["photo_refs"][:3]):
                                                photo_url = agent.get_photo_url(ref)
                                                if photo_url:
                                                    with photo_cols[j]:
                                                        st.image(photo_url, use_container_width=True)
                                        
                                        maps_url = f"https://www.google.com/maps/place/?q=place_id:{loc['place_id']}"
                                        st.markdown(f"[🗺️ Open in Google Maps]({maps_url})")
                            else:
                                st.warning("No locations found. Try a different search.")

# ===========================================
# Tab: Export
# ===========================================

with tab_exports:
    st.subheader("📦 Export Director's Deliverables")
    
    if not selected_project:
        st.warning("⚠️ Select a project first")
    else:
        project = load_project(selected_project)
        
        st.markdown(f"### {project.title_en}")
        
        st.write("**Available Exports:**")
        
        export_options = []
        if project.scenes:
            export_options.append("Scene Breakdown (PDF)")
        if project.concepts:
            export_options.append("Concept Album (PDF)")
        if project.scenes and project.concepts:
            export_options.append("Pitch Deck (PPTX)")
            export_options.append("Storyboard Scroll (PNG)")
        
        selected_export = st.multiselect("Choose exports", export_options)
        
        if st.button("📥 Prepare Exports", type="primary", use_container_width=True):
            st.info("📦 Preparing export package...")
            st.success("✅ Ready for download (coming soon)")

# ===========================================
# Footer
# ===========================================

st.markdown("---")
st.markdown("""
**AI Studio Elsewhere** · 云上电影工作室
Beyond imagination, above the clouds — 云上。

Built for directors by directors. | © 2024-2026
""")
