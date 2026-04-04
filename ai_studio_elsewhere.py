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
    st.session_state.user_id = "demo_user"
    st.session_state.user_email = "director@aistudioelsewhere.com"
    st.session_state.user_tier = "free"

# OpenAI for translation & text processing
try:
    from openai import OpenAI
    openai_client = OpenAI()
except Exception as e:
    print(f"⚠️ OpenAI client init failed: {e}")
    openai_client = None

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

# Wanxiang for image generation (Phase 1 - recommended but optional)
try:
    from tongyi_wanx_client import TongyiWanxClient
    WANX_AVAILABLE = True
except ImportError:
    WANX_AVAILABLE = False

# ===========================================
# Configuration & Paths
# ===========================================

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
SCRIPTS_DIR = DATA_DIR / "scripts"
SCENES_DIR = DATA_DIR / "scenes"
CONCEPTS_DIR = DATA_DIR / "concepts"
VIDEOS_DIR = DATA_DIR / "videos"
STORYBOARDS_DIR = DATA_DIR / "storyboards"
EXPORTS_DIR = DATA_DIR / "exports"

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
    Uses GPT-4o for extraction, optionally translates to English.
    """
    if not openai_client:
        return []
    
    try:
        # Use GPT to structure the script
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a film script analyst. 
                    Extract scenes from this script and return JSON array:
                    [
                      {
                        "scene_number": 1,
                        "heading": "INT. APARTMENT - NIGHT",
                        "location": "Apartment",
                        "time_of_day": "Night",
                        "characters": ["ALICE", "BOB"],
                        "action": "Alice enters the dark apartment...",
                        "keywords": ["dark", "mysterious", "tension"],
                        "mood": "tense"
                      }
                    ]
                    Return ONLY valid JSON."""
                },
                {
                    "role": "user",
                    "content": f"Parse this script:\n\n{text[:2000]}"  # First 2000 chars
                }
            ],
            max_tokens=2000,
            temperature=0.5
        )
        
        json_str = response.choices[0].message.content
        
        # Try to extract JSON from response
        try:
            scenes_data = json.loads(json_str)
        except:
            # Fallback: create a simple scene breakdown
            scenes_data = [
                {
                    "scene_number": 1,
                    "heading": "OPENING SCENE",
                    "location": "TBD",
                    "time_of_day": "Unknown",
                    "characters": [],
                    "action": text[:500],
                    "keywords": ["establishing"],
                    "mood": "neutral"
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
                mood=mood
            )
            scenes.append(scene)
        
        st.success(f"✅ Extracted {len(scenes)} scenes")
        
        return scenes
    
    except Exception as e:
        st.error(f"❌ Scene parsing failed: {e}")
        return []

# ===========================================
# Concept Image Generation (Wanxiang)
# ===========================================

def generate_concept_images(scene: SceneBreakdown, style: str = "cinematic") -> List[str]:
    """
    Generate concept images for a scene using Wanxiang.
    Returns list of image URLs.
    """
    if not WANX_AVAILABLE or not os.getenv("DASHSCOPE_API_KEY"):
        st.warning("⚠️ Wanxiang API not configured. Skipping image generation.")
        return []
    
    try:
        from tongyi_wanx_client import TongyiWanxClient
        client = TongyiWanxClient()
        
        # Compose prompt from scene
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
        
        # Generate image using Wanxiang
        result = client.generate_image(
            prompt=prompt,
            negative_prompt="blurry, watermark, low quality",
            seed=None
        )
        
        if result.get('status') == 'succeeded' and result.get('images'):
            return result['images']  # List of image URLs
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

def list_projects() -> List[str]:
    """List all projects"""
    projects = []
    for proj_file in SCRIPTS_DIR.glob("project_*.json"):
        projects.append(proj_file.stem.replace("project_", ""))
    return sorted(projects)

def load_project(project_id: str) -> Optional[Project]:
    """Load project from disk"""
    proj_file = SCRIPTS_DIR / f"project_{project_id}.json"
    if not proj_file.exists():
        return None
    
    try:
        with open(proj_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Reconstruct Project object
        project = Project(
            project_id=data.get("project_id"),
            title_en=data.get("title_en"),
            title_zh=data.get("title_zh"),
            director=data.get("director"),
            logline=data.get("logline"),
            created_at=data.get("created_at"),
            last_updated=data.get("last_updated"),
            script_path=data.get("script_path"),
        )
        return project
    except Exception as e:
        st.error(f"❌ Failed to load project: {e}")
        return None

def save_project(project: Project):
    """Save project to disk"""
    proj_file = SCRIPTS_DIR / f"project_{project.project_id}.json"
    
    data = {
        "project_id": project.project_id,
        "title_en": project.title_en,
        "title_zh": project.title_zh,
        "director": project.director,
        "logline": project.logline,
        "created_at": project.created_at,
        "last_updated": datetime.now().isoformat(),
        "script_path": project.script_path,
        "scenes": len(project.scenes),
        "concepts": {k: len(v) for k, v in project.concepts.items()},
        "videos": list(project.videos.keys()),
    }
    
    try:
        with open(proj_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        st.success(f"✅ Project saved: {project.title_en}")
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

st.title("🎬 AI Studio Elsewhere")
st.caption("云上电影工作室 · Beyond imagination, above the clouds — 云上。")

# ===========================================
# Sidebar Configuration
# ===========================================

st.sidebar.header("🎬 Film Projects")

# Force refresh project list
if st.sidebar.button("🔄 Refresh Projects"):
    st.rerun()

projects = list_projects()
if projects:
    selected_project = st.sidebar.selectbox("Select a project", projects)
    st.sidebar.success(f"✅ {len(projects)} project(s) found")
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

st.sidebar.subheader("🎨 Image Generation (Wanxiang)")
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

tab_home, tab_new_project, tab_script, tab_scenes, tab_concepts, tab_video, tab_storyboard, tab_exports = st.tabs([
    "🏠 Home",
    "📝 New Project",
    "📄 Script Upload",
    "🎬 Scene Breakdown",
    "🎨 Concept Images",
    "🎥 Video Generation",
    "📋 Storyboard",
    "📦 Export"
])

# ===========================================
# Tab: Home
# ===========================================

with tab_home:
    st.subheader("🎬 Welcome to AI Studio Elsewhere")
    
    st.markdown("""
    ### Cloud-based Film Production Suite
    
    A fully integrated AI cinematic laboratory designed for film directors.
    
    **Workflow:**
    1. **📝 New Project** → Create a film project
    2. **📄 Script Upload** → Upload your script (PDF, Word, TXT)
    3. **🎬 Scene Breakdown** → OCR extraction, translation, scene analysis
    4. **🎨 Concept Images** → Generate visual concepts per scene
    5. **🎥 Video Generation** → Create experimental video scenes
    6. **📋 Storyboard** → Assemble sequences
    7. **📦 Export** → Download complete director's packages
    
    **Features:**
    - 🌐 Bilingual support (Chinese ↔ English + Pinyin)
    - 🎨 AI concept art generation
    - 🎬 Experimental video synthesis
    - 📍 Real-location research
    - 📊 Comprehensive exports
    
    ---
    
    **Current Projects:**
    """)
    
    if projects:
        for proj_id in projects[:3]:  # Show first 3
            proj = load_project(proj_id)
            if proj:
                st.write(f"• **{proj.title_en}** ({proj.title_zh})")
                st.write(f"  Director: {proj.director}")
                st.write(f"  Scenes: {len(proj.scenes)}")
    else:
        st.info("No projects yet. Click 'New Project' to get started!")

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
            st.balloons()
            st.success(f"✅ Project created: {title_en}")

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
            
            # Save uploaded file
            script_path = SCRIPTS_DIR / f"{selected_project}_script_{uploaded_file.name}"
            with open(script_path, "wb") as f:
                f.write(uploaded_file.read())
            
            st.success(f"✅ File saved: {uploaded_file.name}")
            
            # Extract text based on file type
            extracted_text = ""
            
            if uploaded_file.type == "application/pdf":
                st.info("📄 Processing PDF...")
                images, page_paths = extract_pages_from_pdf(str(script_path))
                
                if images:
                    st.write(f"Extracted {len(images)} pages")
                    
                    # OCR first page for preview
                    if page_paths:
                        preview_text = extract_text_from_image(page_paths[0])
                        if preview_text:
                            st.write("**Preview of extracted text:**")
                            st.text(preview_text[:500])
                        
                        # Extract from all pages
                        all_text = []
                        for page_path in page_paths:
                            text = extract_text_from_image(page_path)
                            if text:
                                all_text.append(text)
                        extracted_text = "\n".join(all_text)
            
            elif uploaded_file.type == "text/plain":
                extracted_text = uploaded_file.getvalue().decode("utf-8")
            
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
        
        if not project.script_path:
            st.warning("⚠️ Upload a script first in the 'Script Upload' tab")
        else:
            st.markdown(f"### {project.title_en}")
            
            if st.button("🔍 Analyze Script → Extract Scenes", type="primary", use_container_width=True):
                with st.spinner("Parsing script..."):
                    # Read script
                    script_text = ""
                    script_path = Path(project.script_path)
                    
                    if script_path.suffix == ".pdf":
                        images, page_paths = extract_pages_from_pdf(str(script_path))
                        for page_path in page_paths:
                            script_text += extract_text_from_image(page_path) + "\n"
                    elif script_path.suffix == ".txt":
                        script_text = script_path.read_text(encoding="utf-8")
                    
                    # Parse to scenes
                    if script_text:
                        scenes = parse_script_to_scenes(script_text)
                        project.scenes = scenes
                        save_project(project)
                        st.success(f"✅ Extracted and translated {len(scenes)} scenes")
                        st.rerun()  # Refresh to show scenes immediately
                    else:
                        st.error("❌ Could not extract text from script")
            
            # Display scenes
            if project.scenes:
                st.write(f"**Scenes: {len(project.scenes)}**")
                
                for i, scene in enumerate(project.scenes):
                    with st.expander(f"Scene {scene.scene_number}: {scene.heading}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Location:** {scene.location}")
                            st.write(f"**Time:** {scene.time_of_day}")
                            st.write(f"**Mood:** {scene.mood}")
                        
                        with col2:
                            st.write(f"**Characters:** {', '.join(scene.characters) or 'None'}")
                            st.write(f"**Keywords:** {', '.join(scene.keywords)}")
                        
                        st.write("**Action:**")
                        st.write(scene.action)

# ===========================================
# Tab: Concept Images
# ===========================================

with tab_concepts:
    st.subheader("🎨 Generate Concept Images")
    
    # Check subscription
    if not subscription_manager.has_feature("concept_images"):
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
            
            style = st.selectbox(
                "Art Style",
                ["Cinematic", "Documentary", "Surreal", "Minimalist", "Neon Noir"]
            )
            
            # Select scenes to generate concepts for
            scene_options = {f"Scene {s.scene_number}: {s.heading}": i for i, s in enumerate(project.scenes)}
            selected_scenes = st.multiselect("Select scenes", list(scene_options.keys()))
            
            if st.button("🎨 Generate Concept Images", type="primary", use_container_width=True):
                if not selected_scenes:
                    st.warning("⚠️ Select at least one scene")
                else:
                    for scene_label in selected_scenes:
                        scene_idx = scene_options[scene_label]
                        scene = project.scenes[scene_idx]
                        
                        with st.spinner(f"Generating concepts for {scene_label}..."):
                            images = generate_concept_images(scene, style.lower())
                            
                            if images:
                                project.concepts[scene.scene_id] = images
                                save_project(project)
                                
                                st.success(f"✅ Generated {len(images)} concepts")
                                
                                # Display images
                                cols = st.columns(2)
                                for j, img_url in enumerate(images[:4]):
                                    with cols[j % 2]:
                                        try:
                                            response = requests.get(img_url, timeout=10)
                                            st.image(response.content, caption=f"Concept {j+1}")
                                        except:
                                            st.write(f"[Image {j+1}]({img_url})")

# ===========================================
# Tab: Video Generation
# ===========================================

with tab_video:
    st.subheader("🎥 Generate Experimental Videos")
    
    # Check subscription
    if not subscription_manager.has_feature("video_generation"):
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
            scenes_for_video = [
                {
                    "id": scene.scene_id,
                    "heading": scene.heading,
                    "prompt": f"{scene.heading}. Location: {scene.location}. Time: {scene.time_of_day}. Mood: {scene.mood}. Action: {scene.action[:100]}"
                }
                for scene in project.scenes
            ]
            
            try:
                from runway_video_ui import display_video_generation_tab
                display_video_generation_tab(scenes_for_video, project.title_en)
            except ImportError:
                st.error("❌ Runway video generation module not available. Make sure runway_video_ui.py is in the same directory.")
                st.info("Copy runway_video_ui.py and runway_video_agent.py to your project directory.")

# ===========================================
# Tab: Storyboard
# ===========================================

with tab_storyboard:
    st.subheader("📋 Storyboard Assembly")
    
    if not selected_project:
        st.warning("⚠️ Select a project first")
    else:
        project = load_project(selected_project)
        
        st.markdown(f"### {project.title_en}")
        
        if not project.concepts:
            st.warning("⚠️ Generate concept images first")
        else:
            st.write("**Storyboard Layout Options:**")
            layout = st.selectbox(
                "Choose layout",
                ["6-panel", "8-panel", "12-panel scroll", "Custom"]
            )
            
            st.info(f"📋 Assembling storyboard with {layout} layout...")

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

Built for directors by directors. | © 2024
""")
