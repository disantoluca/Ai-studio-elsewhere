#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Integration Layer for AI Studio Elsewhere
Connects all your agents to the Streamlit app
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add agents to path - try multiple locations
AGENTS_DIR = Path(__file__).parent / "agents"
if AGENTS_DIR.exists():
    sys.path.insert(0, str(AGENTS_DIR))
    print(f"✅ Found agents at: {AGENTS_DIR}")
else:
    # Try current directory
    sys.path.insert(0, ".")
    sys.path.insert(0, str(Path.cwd() / "agents"))
    print(f"⚠️ Agents directory not found at {AGENTS_DIR}")
    print(f"   Trying: {Path.cwd() / 'agents'}")

print("🔌 Loading Agent Integration Layer...")

# ============================================================
# 1. OCR EXTRACTOR AGENT
# ============================================================

def load_ocr_agent():
    """Load OCR extractor for text extraction from images"""
    try:
        from ocr_extractor import ManualTextExtractor
        print("✅ OCR Extractor loaded")
        return ManualTextExtractor()
    except ImportError as e:
        print(f"⚠️  OCR Extractor failed to load: {e}")
        return None

_ocr_agent = None

def get_ocr_agent():
    global _ocr_agent
    if _ocr_agent is None:
        _ocr_agent = load_ocr_agent()
    return _ocr_agent

def extract_text_from_image_with_agent(image_path: str) -> str:
    """
    Extract text from image using your OCR agent
    Replaces the stub EasyOCR function
    """
    agent = get_ocr_agent()
    if agent:
        try:
            result = agent.extract_text_from_image(image_path)
            if result.get("status") == "success":
                return result.get("text", "")
            else:
                print(f"⚠️ OCR Error: {result.get('error')}")
                return ""
        except Exception as e:
            print(f"⚠️ OCR extraction failed: {e}")
            return ""
    return ""

# ============================================================
# 2. CHINESE TEXT AGENT
# ============================================================

_chinese_text_agent = None

def load_chinese_text_agent():
    """Load Chinese text expert for translation and analysis"""
    try:
        from chinese_text_agent import ChineseTextExpertAgent
        print("✅ Chinese Text Expert Agent loaded")
        try:
            return ChineseTextExpertAgent()
        except FileNotFoundError as e:
            print(f"⚠️  Config not found: {e}")
            print("   Trying to create default config...")
            # Create a default config if missing
            import json
            from pathlib import Path
            config_path = Path("agent_config.json")
            if not config_path.exists():
                default_config = {
                    "api_key": "",
                    "model": "qwen-vl-max",
                    "system_prompt": {
                        "en": "You are a Chinese language expert.",
                        "zh": "你是中文专家。"
                    }
                }
                with open(config_path, 'w') as f:
                    json.dump(default_config, f)
                print("   ✅ Created default config")
            return ChineseTextExpertAgent()
    except ImportError as e:
        print(f"⚠️  Chinese Text Agent failed to load: {e}")
        return None
    except Exception as e:
        print(f"⚠️  Chinese Text Agent error: {e}")
        return None

def get_chinese_text_agent():
    global _chinese_text_agent
    if _chinese_text_agent is None:
        _chinese_text_agent = load_chinese_text_agent()
    return _chinese_text_agent

def translate_with_agent(text_zh: str) -> str:
    """Translate Chinese to English using your agent"""
    agent = get_chinese_text_agent()
    if agent:
        try:
            response = agent.process(text_zh, task="translate")
            return response.content_en or response.content
        except Exception as e:
            print(f"⚠️ Translation error: {e}")
            return ""
    return ""

def analyze_scene_with_agent(text: str) -> Dict:
    """Analyze scene text for mood, keywords, etc."""
    agent = get_chinese_text_agent()
    if agent:
        try:
            response = agent.process(text, task="analyze")
            return {
                "analysis": response.content,
                "zh": response.content_zh,
                "en": response.content_en
            }
        except Exception as e:
            print(f"⚠️ Analysis error: {e}")
            return {"analysis": text}
    return {"analysis": text}

# ============================================================
# 3. PAINTER AGENT (Image Generation)
# ============================================================

_painter_agent = None

def load_painter_agent():
    """Load Painter agent for concept image generation"""
    try:
        from painter_agent import PainterAgent, PainterParameters
        print("✅ Painter Agent loaded")
        return PainterAgent(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            region=os.getenv("DASHSCOPE_REGION", "intl"),
            model=os.getenv("DASHSCOPE_IMAGE_MODEL", "wanx-v1")
        )
    except ImportError as e:
        print(f"⚠️  Painter Agent failed to load: {e}")
        return None
    except RuntimeError as e:
        print(f"⚠️  Painter Agent initialization failed: {e}")
        return None

def get_painter_agent():
    global _painter_agent
    if _painter_agent is None:
        _painter_agent = load_painter_agent()
    return _painter_agent

def generate_concept_images_with_agent(scene_heading: str, scene_data: Dict) -> List[str]:
    """Generate concept images using your Painter Agent"""
    agent = get_painter_agent()
    if not agent:
        print("⚠️ Painter Agent not available")
        return []
    
    try:
        from painter_agent import PainterParameters
        
        # Build parameters
        params = PainterParameters(
            subject=scene_heading,
            style=["cinematic", "moody"],
            negative=["blurry", "watermark", "low quality"],
            aspect_ratio="16:9",
            steps=4,
            seed=None
        )
        
        # Build step descriptions
        step_descriptions = [
            f"Wide establishing shot: {scene_data.get('location', 'location')}",
            f"Character focus: {', '.join(scene_data.get('characters', ['unnamed'])[:2])}",
            f"Action focus: {scene_data.get('action', 'scene action')[:100]}",
            f"Mood and atmosphere: {scene_data.get('mood', 'atmospheric')}"
        ]
        
        # Generate
        result = agent.generate_lesson(params, step_descriptions)
        
        # Return image paths
        image_urls = [panel["path"] for panel in result.get("panels", [])]
        if result.get("final"):
            image_urls.append(result["final"])
        
        return image_urls
    
    except Exception as e:
        print(f"⚠️ Concept generation failed: {e}")
        return []

# ============================================================
# 4. PROMPT COMPOSER AGENT
# ============================================================

_prompt_composer = None

def load_prompt_composer_agent():
    """Load prompt composer for enhanced prompts"""
    try:
        from prompt_composer_agent import PromptComposerAgent
        print("✅ Prompt Composer Agent loaded")
        return PromptComposerAgent()
    except ImportError as e:
        print(f"⚠️  Prompt Composer Agent failed to load: {e}")
        return None

def get_prompt_composer_agent():
    global _prompt_composer
    if _prompt_composer is None:
        _prompt_composer = load_prompt_composer_agent()
    return _prompt_composer

def compose_prompt_for_scene(scene_data: Dict) -> str:
    """Compose enhanced prompt for scene generation"""
    agent = get_prompt_composer_agent()
    if agent:
        try:
            result = agent.compose_scene_prompt(scene_data)
            return result.get("prompt_en", "")
        except Exception as e:
            print(f"⚠️ Prompt composition failed: {e}")
            return ""
    return ""

# ============================================================
# 5. MOTION CONTROL AGENT
# ============================================================

_motion_control = None

def load_motion_control_agent():
    """Load motion control for video generation"""
    try:
        from motion_control_agent import apply_motion_to_prompt, get_supported_motions
        print("✅ Motion Control Agent loaded")
        return {"apply": apply_motion_to_prompt, "get_motions": get_supported_motions}
    except ImportError as e:
        print(f"⚠️  Motion Control Agent failed to load: {e}")
        return None

def get_motion_control_agent():
    global _motion_control
    if _motion_control is None:
        _motion_control = load_motion_control_agent()
    return _motion_control

def apply_motion_to_video_prompt(prompt: str, motion_type: str) -> str:
    """Apply motion control to video generation prompt"""
    agent = get_motion_control_agent()
    if agent:
        try:
            enhanced_prompt, _ = agent["apply"](prompt, motion_type)
            return enhanced_prompt
        except Exception as e:
            print(f"⚠️ Motion control failed: {e}")
            return prompt
    return prompt

# ============================================================
# 6. MULTI-ANGLE AGENT
# ============================================================

_multi_angle = None

def load_multi_angle_agent():
    """Load multi-angle agent for multi-perspective generation"""
    try:
        from multi_angle_agent import get_multi_angle_agent
        print("✅ Multi-Angle Agent loaded")
        return get_multi_angle_agent()
    except ImportError as e:
        print(f"⚠️  Multi-Angle Agent failed to load: {e}")
        return None

def get_multi_angle_agent_instance():
    global _multi_angle
    if _multi_angle is None:
        _multi_angle = load_multi_angle_agent()
    return _multi_angle

# ============================================================
# 7. VIDEO TRANSLATOR AGENT
# ============================================================

_video_translator = None

def load_video_translator_agent():
    """Load video translator for subtitles and dubbing"""
    try:
        from video_translator_agent import VideoTranslatorAgent
        api_key = os.getenv("ALLVOICELAB_API_KEY")
        if not api_key:
            print("⚠️  Video Translator Agent: No ALLVOICELAB_API_KEY provided")
            return None
        print("✅ Video Translator Agent loaded")
        return VideoTranslatorAgent(api_key=api_key)
    except ImportError as e:
        print(f"⚠️  Video Translator Agent failed to load: {e}")
        return None
    except Exception as e:
        print(f"⚠️  Video Translator Agent error: {e}")
        return None

def get_video_translator_agent():
    global _video_translator
    if _video_translator is None:
        _video_translator = load_video_translator_agent()
    return _video_translator

# ============================================================
# 8. GOOGLE PLACES SCRAPER
# ============================================================

_location_scraper = None

def load_location_scraper():
    """Load Google Places scraper for location research"""
    try:
        from google_places_scraper import GooglePlacesAPI
        api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if api_key:
            print("✅ Google Places Scraper loaded")
            return GooglePlacesAPI(api_key)
        else:
            print("⚠️  Google Places API key not configured")
            return None
    except ImportError as e:
        print(f"⚠️  Location Scraper failed to load: {e}")
        return None

def get_location_scraper():
    global _location_scraper
    if _location_scraper is None:
        _location_scraper = load_location_scraper()
    return _location_scraper

def scrape_location_data(location: str, category: str = None) -> List[Dict]:
    """Scrape real location data using Google Places"""
    agent = get_location_scraper()
    if agent:
        try:
            results = agent.search_brand_locations(location, "US", category, max_results=10)
            return [
                {
                    "name": r.name,
                    "address": r.address,
                    "city": r.city,
                    "rating": r.rating,
                    "phone": r.phone,
                    "website": r.website
                }
                for r in results
            ]
        except Exception as e:
            print(f"⚠️ Location scraping failed: {e}")
            return []
    return []

# ============================================================
# 9. IMAGE PROCESSOR
# ============================================================

_image_processor = None

def load_image_processor():
    """Load image processor for format handling"""
    try:
        from image_processor import ImageProcessor
        print("✅ Image Processor loaded")
        return ImageProcessor()
    except ImportError as e:
        print(f"⚠️  Image Processor failed to load: {e}")
        return None

def get_image_processor():
    global _image_processor
    if _image_processor is None:
        _image_processor = load_image_processor()
    return _image_processor

# ============================================================
# INITIALIZATION STATUS
# ============================================================

def get_agent_status() -> Dict:
    """Get status of all loaded agents"""
    return {
        "ocr": get_ocr_agent() is not None,
        "chinese_text": get_chinese_text_agent() is not None,
        "painter": get_painter_agent() is not None,
        "prompt_composer": get_prompt_composer_agent() is not None,
        "motion_control": get_motion_control_agent() is not None,
        "multi_angle": get_multi_angle_agent_instance() is not None,
        "video_translator": get_video_translator_agent() is not None,
        "location_scraper": get_location_scraper() is not None,
        "image_processor": get_image_processor() is not None,
    }

print("🎬 Agent Integration Layer Ready!")
print("=" * 60)
status = get_agent_status()
for agent_name, loaded in status.items():
    symbol = "✅" if loaded else "⚠️"
    print(f"{symbol} {agent_name.replace('_', ' ').title()}")
print("=" * 60)
