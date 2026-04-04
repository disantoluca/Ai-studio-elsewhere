# 🎬 AI Studio Elsewhere - Implementation Guide
## Film Director's Cloud Studio · 云上电影工作室

---

## 📋 Table of Contents

1. **Quick Start**
2. **Architecture Overview**
3. **Agent Integration Checklist**
4. **Phase 1: MVP (Script → Scenes → Concepts)**
5. **Phase 2: Video Generation**
6. **Phase 3: Advanced Features**
7. **Deployment & Testing**

---

## 🚀 Quick Start

### Prerequisites
```bash
# Core dependencies
pip install streamlit pillow python-dotenv openai requests

# Optional (based on your setup)
pip install pdf2image        # PDF processing
pip install easyocr          # OCR
pip install paddleocr        # Alternative OCR
pip install runway-sdk       # Video generation

# System dependencies (macOS with Homebrew)
brew install poppler         # For pdf2image
```

### Environment Variables
```bash
# Create .env file in project directory
OPENAI_API_KEY=sk-...
DASHSCOPE_API_KEY=sk-...
RUNWAY_API_KEY=...
PYTHON_PATH=/path/to/agents
```

### Run the App
```bash
cd /path/to/project
streamlit run ai_studio_elsewhere.py
```

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Streamlit UI Layer                         │
│          (ai_studio_elsewhere.py - 700+ lines)              │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
  ┌─────────────┐ ┌────────────┐ ┌──────────────┐
  │Script Upload│ │Scene Parser│ │Image Generator
  │  & OCR      │ │ (GPT-4o)   │ │  (Wanxiang)
  │             │ │            │ │
  │ - PDF       │ │ - Extract  │ │ - Concepts
  │ - Word      │ │ - Structure│ │ - Variations
  │ - Images    │ │ - Analyze  │ │ - Styles
  └─────────────┘ └────────────┘ └──────────────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
  ┌─────────────┐ ┌────────────┐ ┌──────────────┐
  │Translator   │ │Real Location│ │Video Generator
  │ (OpenAI)    │ │ Research    │ │   (Runway)
  │             │ │             │ │
  │ - English   │ │ - Google    │ │ - Motion Control
  │ - Pinyin    │ │ - Scrape    │ │ - Multi-angle
  │ - Analysis  │ │ - Map View  │ │ - Variations
  └─────────────┘ └────────────┘ └──────────────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
  ┌─────────────┐ ┌────────────┐ ┌──────────────┐
  │Storyboard   │ │Export Center│ │Director Dash
  │ Assembly    │ │             │ │
  │             │ │ - PDF       │ │ - Analytics
  │ - 6-panel   │ │ - PPTX      │ │ - Progress
  │ - 8-panel   │ │ - ZIP       │ │ - Settings
  │ - Scroll    │ │ - Video Reel│ │
  └─────────────┘ └────────────┘ └──────────────┘
        │              │              │
        └──────────────┴──────────────┘
                       │
                 Data Persistence
                (JSON + file storage)
```

---

## ✅ Agent Integration Checklist

### Phase 1: MVP (PRIORITY)
- [ ] **Script Upload** (pdf2image → PIL)
- [ ] **OCR Extraction** (EasyOCR or your ocr_extractor.py)
- [ ] **Chinese Text Processing** (chinese_text_agent.py)
- [ ] **Scene Breakdown** (GPT-4o parsing)
- [ ] **Translation** (openai_client + english translation)
- [ ] **Concept Images** (painter_agent.py + Wanxiang)

### Phase 2: Video
- [ ] **Motion Control Agent** (motion_control_agent.py)
- [ ] **Runway Integration** (runway.py + multi_angle_agent.py)
- [ ] **Video Translator** (video_translator_agent.py for subtitles)

### Phase 3: Advanced
- [ ] **Real Location Research** (google_places_scraper.py)
- [ ] **Voice Lab** (all_voice_lab.py for narration)
- [ ] **CHDC Transitions** (chdc_prompt_engine.py)
- [ ] **Storyboard Exporter** (custom assembly)

### Phase 4: Polish
- [ ] **Prompt Reviewer** (prompt_reviewer.py)
- [ ] **Director Dashboard** (analytics + settings)
- [ ] **Batch Processing** (orchestrator_agent.py)

---

## 📦 Phase 1: MVP Implementation

### Step 1: Integrate OCR Extractor

**Your existing agent:** `ocr_extractor.py` (from Digital Library Management)

**Integration point:** Script Upload tab

```python
# In ai_studio_elsewhere.py, replace:
def extract_text_from_image(image_path: str) -> str:
    """Extract text from image using OCR"""
    if not EASYOCR_AVAILABLE:
        return ""
    
    # OPTION A: Use EasyOCR (built-in)
    reader = get_ocr_reader()
    result = reader.readtext(image_path)
    text = "\n".join([item[1] for item in result])
    return text

# OPTION B: Use your ocr_extractor.py (recommended!)
# ============================================================

from ocr_extractor import OCRExtractor

_ocr_engine = None

def get_ocr_extractor():
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = OCRExtractor()  # Your existing class
    return _ocr_engine

def extract_text_from_image(image_path: str) -> str:
    """Extract text using your OCR engine"""
    try:
        engine = get_ocr_extractor()
        result = engine.extract(image_path)  # Your method name
        return result.get("text", "")
    except Exception as e:
        print(f"❌ OCR error: {e}")
        return ""
```

**Action needed:**
1. Check the function signature of your `ocr_extractor.py`
2. Replace `extract_text_from_image()` with your actual implementation
3. Test with a sample PDF page

---

### Step 2: Integrate Chinese Text Agent

**Your existing agent:** `chinese_text_agent.py`

**Integration point:** Scene Breakdown tab (for analysis + translation)

```python
# In ai_studio_elsewhere.py

from chinese_text_agent import ChineseTextExpertAgent

_chinese_agent = None

def get_chinese_agent():
    global _chinese_agent
    if _chinese_agent is None:
        _chinese_agent = ChineseTextExpertAgent(
            config_path="agent_config.json"  # Your config
        )
    return _chinese_agent

def analyze_scene_text(text_zh: str) -> Dict[str, str]:
    """
    Use Chinese Text Expert Agent to analyze scene text.
    Extracts keywords, mood, characters, etc.
    """
    try:
        agent = get_chinese_agent()
        response = agent.process(
            text=text_zh,
            task="analyze"  # analyze | translate | explain | ocr_review
        )
        
        return {
            "analysis": response.content,
            "zh": response.content_zh,
            "en": response.content_en
        }
    except Exception as e:
        print(f"⚠️ Agent error: {e}")
        return {"analysis": text_zh}

def translate_chinese_to_english(text_zh: str) -> str:
    """
    Use Chinese Text Expert Agent for translation.
    """
    try:
        agent = get_chinese_agent()
        response = agent.process(
            text=text_zh,
            task="translate"
        )
        return response.content_en or response.content
    except Exception as e:
        print(f"⚠️ Translation error: {e}")
        # Fallback to OpenAI
        return translate_to_english(text_zh)
```

**Action needed:**
1. Verify `ChineseTextExpertAgent` class structure
2. Check available methods and task types
3. Update function calls to match your API

---

### Step 3: Integrate Painter Agent

**Your existing agent:** `painter_agent.py` + `painter_agent_api.py`

**Integration point:** Concept Images tab

```python
# In ai_studio_elsewhere.py

from painter_agent import PainterAgent, PainterParameters
from prompt_composer_agent import PromptComposerAgent

_painter = None
_prompt_composer = None

def get_painter():
    global _painter
    if _painter is None:
        _painter = PainterAgent(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            region=os.getenv("DASHSCOPE_REGION", "intl"),
            model=os.getenv("DASHSCOPE_IMAGE_MODEL", "wanx-v1")
        )
    return _painter

def get_prompt_composer():
    global _prompt_composer
    if _prompt_composer is None:
        _prompt_composer = PromptComposerAgent()
    return _prompt_composer

def generate_concept_images(scene: SceneBreakdown, style: str = "cinematic") -> List[str]:
    """
    Generate concept images using Painter Agent.
    """
    try:
        painter = get_painter()
        
        # Compose prompt from scene
        prompt_text = f"""
        Film Scene Concept Art:
        
        Title: {scene.heading}
        Location: {scene.location}
        Time: {scene.time_of_day}
        Mood: {scene.mood}
        
        Action: {scene.action[:500]}
        """
        
        # Create painter parameters
        params = PainterParameters(
            subject=scene.heading,
            style=[style.lower()],
            negative=["blurry", "watermark", "low quality"],
            aspect_ratio="16:9",  # Cinematic
            seed=None,
            steps=4
        )
        
        # Generate step-by-step concepts
        step_descriptions = [
            f"Establishing shot: {scene.location}",
            f"Character focus: {', '.join(scene.characters[:2]) or 'unnamed'}",
            f"Action: {scene.action[:100]}",
            f"Mood/atmosphere: {scene.mood}"
        ]
        
        result = painter.generate_lesson(params, step_descriptions)
        
        image_urls = [panel["path"] for panel in result["panels"]]
        if result["final"]:
            image_urls.append(result["final"])
        
        return image_urls
    
    except Exception as e:
        st.error(f"❌ Image generation failed: {e}")
        return []
```

**Action needed:**
1. Verify `PainterAgent` initialization
2. Check `generate_lesson()` return format
3. Test with sample scene data

---

### Step 4: Scene Breakdown Pipeline

**Integrating GPT-4o for structure + your agents for translation**

```python
def parse_script_to_scenes(text: str) -> List[SceneBreakdown]:
    """
    Parse script to scenes using GPT-4o,
    then enrich with Chinese text analysis.
    """
    if not openai_client:
        return []
    
    try:
        # Step 1: GPT parses structure
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "system",
                "content": """Film script analyst. Extract scenes as JSON:
                [{
                  "scene_number": 1,
                  "heading": "INT. APARTMENT - NIGHT",
                  "location": "Apartment",
                  "time_of_day": "Night",
                  "characters": ["ALICE", "BOB"],
                  "action": "...",
                  "keywords": [],
                  "mood": ""
                }]"""
            }, {
                "role": "user",
                "content": f"Parse:\n\n{text[:2000]}"
            }],
            max_tokens=2000,
            temperature=0.5
        )
        
        json_str = response.choices[0].message.content
        
        try:
            scenes_data = json.loads(json_str)
        except:
            scenes_data = [{
                "scene_number": 1,
                "heading": "OPENING",
                "location": "TBD",
                "time_of_day": "Unknown",
                "characters": [],
                "action": text[:500],
                "keywords": ["establishing"],
                "mood": "neutral"
            }]
        
        # Step 2: Enrich with Chinese analysis (if text is Chinese)
        scenes = []
        for scene_data in scenes_data:
            scene = SceneBreakdown(
                scene_id=f"scene_{len(scenes)+1:03d}",
                **scene_data
            )
            
            # If action is in Chinese, analyze with agent
            if any('\u4e00' <= c <= '\u9fff' for c in scene.action):
                analysis = analyze_scene_text(scene.action)
                scene.keywords = scene.keywords or analysis.get("keywords", [])
                scene.mood = scene.mood or analysis.get("mood", "")
            
            scenes.append(scene)
        
        return scenes
    
    except Exception as e:
        st.error(f"❌ Scene parsing failed: {e}")
        return []
```

---

## 🎬 Phase 2: Video Generation

### Runway Integration

**Your existing agents:** `runway.py`, `motion_control_agent.py`, `multi_angle_agent.py`

```python
def generate_video_scene(
    scene: SceneBreakdown,
    concept_image_url: Optional[str] = None,
    shot_type: str = "static",
    lighting: str = "natural"
) -> Optional[str]:
    """
    Generate experimental video using Runway.
    """
    if not RUNWAY_AVAILABLE:
        st.warning("⚠️ Runway SDK not available")
        return None
    
    try:
        # Prepare prompt from scene
        prompt = f"""
        Film scene video generation:
        
        Scene: {scene.heading}
        Shot type: {shot_type}
        Lighting: {lighting}
        Mood: {scene.mood}
        
        Action: {scene.action}
        """
        
        # Call Runway API (pseudocode - adjust to actual API)
        # See: https://docs.runwayml.com/
        
        # Option 1: Direct Runway client
        # from runway import Runway
        # client = Runway(api_token=os.getenv("RUNWAY_API_KEY"))
        # task = client.tasks.create(
        #     model="stable-diffusion-v1-5",
        #     inputs={
        #         "prompt": prompt,
        #         "height": 1080,
        #         "width": 1920
        #     }
        # )
        
        st.info("🎥 Runway integration stub - implement actual API call")
        return None
    
    except Exception as e:
        st.error(f"❌ Video generation failed: {e}")
        return None
```

---

## 🔧 Deployment & Testing

### Testing Checklist

```python
# test_studio.py

import streamlit as st
from ai_studio_elsewhere import *

def test_script_upload():
    """Test PDF upload and text extraction"""
    test_pdf = "sample_script.pdf"
    images, pages = extract_pages_from_pdf(test_pdf)
    assert len(images) > 0, "PDF extraction failed"
    print("✅ PDF extraction works")

def test_ocr():
    """Test OCR on sample image"""
    test_image = "sample_page.png"
    text = extract_text_from_image(test_image)
    assert len(text) > 0, "OCR failed"
    print(f"✅ OCR extracted {len(text)} characters")

def test_translation():
    """Test Chinese → English translation"""
    test_text = "这是一个测试。"
    translation = translate_to_english(test_text)
    assert len(translation) > 0, "Translation failed"
    print(f"✅ Translation: {translation}")

def test_scene_parsing():
    """Test script → scenes conversion"""
    test_script = """
    INT. APARTMENT - NIGHT
    
    Alice enters the dark apartment.
    She looks around cautiously.
    
    ALICE: Hello?
    
    EXT. ROOFTOP - DAY
    
    The city sprawls below.
    """
    scenes = parse_script_to_scenes(test_script)
    assert len(scenes) > 0, "Scene parsing failed"
    print(f"✅ Parsed {len(scenes)} scenes")

def test_concept_generation():
    """Test image generation"""
    test_scene = SceneBreakdown(
        scene_id="test_001",
        scene_number=1,
        heading="INT. APARTMENT - NIGHT",
        location="Apartment",
        time_of_day="Night",
        characters=["ALICE"],
        action="Alice enters.",
        dialogue=[],
        keywords=["dark", "tense"],
        mood="mysterious"
    )
    images = generate_concept_images(test_scene)
    assert len(images) >= 0, "Concept generation failed"
    print(f"✅ Generated {len(images)} concept images")

if __name__ == "__main__":
    test_script_upload()
    test_ocr()
    test_translation()
    test_scene_parsing()
    test_concept_generation()
    print("\n✅ All tests passed!")
```

### Running Tests

```bash
# Install test dependencies
pip install pytest

# Run tests
python test_studio.py

# Run with Streamlit
streamlit run ai_studio_elsewhere.py --logger.level=debug
```

---

## 📊 Example Workflow

### Scenario: Director Li Jue's New Film

**Day 1: Project Setup**
```
1. Open AI Studio Elsewhere
2. Click "New Project"
   - Title: "Yangzi's Confusion"
   - Title (Chinese): "颜子的困惑"
   - Director: "Li Jue"
   - Logline: "A young filmmaker navigates identity and artistic expression"
3. Click "Create Project"
```

**Day 2: Script Upload & OCR**
```
1. Go to "Script Upload" tab
2. Upload "yangzi_script_draft1.pdf"
   - App extracts 45 pages
   - OCR extracts ~8,000 characters of Chinese text
3. Preview shows scene headings and dialogue
```

**Day 3: Scene Analysis**
```
1. Go to "Scene Breakdown" tab
2. Click "Analyze Script → Extract Scenes"
   - GPT-4o parses → 13 scenes identified
   - Chinese Text Agent analyzes mood, characters
   - Scene 1: "INT. UNIVERSITY CLASSROOM - DAY"
   - Scene 2: "INT. DORMITORY ROOM - NIGHT"
   - ... etc
3. Each scene shows location, characters, keywords
```

**Day 4: Concept Art**
```
1. Go to "Concept Images" tab
2. Select style: "Cinematic"
3. Select scenes: [1, 3, 5, 7]
4. Click "Generate Concept Images"
   - Painter Agent generates 4 images per scene
   - Each shows different composition
5. Review and save favorites
```

**Day 5: Video Scenes (Future)**
```
1. Go to "Video Generation" tab
2. Select Scene 1
3. Choose shot type: "Dolly In"
4. Runway generates 5-20 second clip
5. Director reviews variations
```

**Day 6: Storyboard Assembly**
```
1. Go to "Storyboard" tab
2. Select 6-panel layout
3. Arrange concept images in sequence
4. Auto-add CHDC transitions
5. Export as PDF scroll
```

**Day 7: Final Export**
```
1. Go to "Export" tab
2. Select exports:
   - Scene Breakdown (PDF)
   - Concept Album (PDF)
   - Storyboard Scroll (PNG)
   - Pitch Deck (PPTX)
3. Click "Prepare Exports"
4. Download complete package
```

---

## 🎯 Success Criteria

### MVP Phase (Week 1-2)
- ✅ Create project
- ✅ Upload script (PDF/text)
- ✅ Extract text with OCR
- ✅ Parse into scenes
- ✅ Translate to English + Pinyin
- ✅ Generate concept images
- ✅ Export scene breakdown

### Phase 2 (Week 3-4)
- ✅ Generate video scenes (Runway)
- ✅ Motion control variations
- ✅ Multi-angle perspectives
- ✅ Video exports

### Phase 3 (Week 5-6)
- ✅ Real location research
- ✅ Voiceover narration
- ✅ CHDC transitions
- ✅ Complete director dashboard
- ✅ Batch processing

---

## 📞 Support

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: pdf2image` | `pip install pdf2image` + `brew install poppler` |
| `OPENAI_API_KEY not set` | Add to .env file or export as env var |
| `No agents found` | Check PYTHONPATH includes agent directory |
| OCR text garbled | Ensure image quality ≥ 300 DPI |
| Video generation fails | Verify Runway API key and quota |

### Next Steps

1. **Copy `ai_studio_elsewhere.py` to your project**
2. **Place agent files in same directory or update imports**
3. **Set environment variables**
4. **Run `streamlit run ai_studio_elsewhere.py`**
5. **Test with sample script**

---

## 📝 Notes for Integration

### Your Agents - Integration Points

| Agent | File | Used In | Status |
|-------|------|---------|--------|
| OCR Extractor | ocr_extractor.py | Script Upload | Ready |
| Chinese Text Expert | chinese_text_agent.py | Scene Analysis | Ready |
| Painter Agent | painter_agent.py | Concept Generation | Ready |
| Prompt Composer | prompt_composer_agent.py | Image Prompts | Ready |
| Motion Control | motion_control_agent.py | Video Variations | Phase 2 |
| Runway Integration | runway.py | Video Generation | Phase 2 |
| Video Translator | video_translator_agent.py | Subtitles | Phase 2 |
| CHDC Prompt Engine | chdc_prompt_engine.py | Transitions | Phase 3 |
| Voice Lab | all_voice_lab.py | Narration | Phase 3 |
| Real Data Scraper | scrape_real_data.py | Location Research | Phase 3 |

### Before You Start

1. Verify each agent's **exact function signatures**
2. Test agents independently first
3. Create unit tests for each integration
4. Document any API changes needed

---

## 🎬 Ready to Build?

The MVP app is ready. Next steps:

1. **Review** `ai_studio_elsewhere.py` architecture
2. **Update** function signatures to match your agents
3. **Test** each integration phase
4. **Deploy** to Streamlit Cloud or your server

```bash
# Deploy to Streamlit Cloud
streamlit deploy ai_studio_elsewhere.py
```

**Good luck, director!** 🚀

---

*Built for Li Jue, Qin Xiaoyue, and all independent filmmakers.*  
*"Beyond imagination, above the clouds — 云上。"*
