# 🎨 SLEEPLESS BLUE NIGHTS PROMPT LIBRARY — INTEGRATION GUIDE

## What You Just Got

A complete, production-ready prompt library with:

✅ **44+ Visual Prompts** (Concept Images, Video, Ink Transitions, Locations, Actor Consistency)
✅ **13 Color Script Frames** (Emotional journey mapped by color)
✅ **2 Director's Statements** (English + Chinese, festival-ready)
✅ **8 Color Motifs** (With emotional meanings and hex codes)
✅ **Runway Integration Ready** (Motion control, multi-angle, actor consistency)
✅ **CHDC Transition Prompts** (Ink blooms, dissolves, reveals)

---

## Files Created

1. **sleepless_blue_nights_prompt_library.py** (Main library - 400+ lines)
   - All prompts in Python dataclasses
   - Color script with emotional journey
   - Director's statements bilingual
   - Helper functions for filtering/exporting

2. **sleepless_blue_nights_ui.py** (Streamlit UI - 350+ lines)
   - Beautiful interactive interface
   - Browse all prompts
   - View color script with color picker
   - Download director's statement
   - Quick prompt selector widget

---

## Integration: Option A — Standalone App (5 minutes)

Run the library as a standalone Streamlit app:

```bash
# Copy both files
cp /mnt/user-data/outputs/sleepless_blue_nights_prompt_library.py .
cp /mnt/user-data/outputs/sleepless_blue_nights_ui.py .

# Run it
streamlit run sleepless_blue_nights_ui.py
```

You'll see:
- 📚 All prompts organized by type
- 🌈 Color script with visual reference
- 🎬 Director's statements
- 📊 Library statistics

---

## Integration: Option B — Into AI Studio Elsewhere (10 minutes)

Add the prompt library to your main app:

### Step 1: Copy the library files

```bash
cp /mnt/user-data/outputs/sleepless_blue_nights_prompt_library.py .
```

### Step 2: Add a tab to ai_studio_elsewhere.py

Add this import at the top:

```python
try:
    from sleepless_blue_nights_prompt_library import (
        get_prompts_by_type, get_color_script_by_act,
        DIRECTOR_STATEMENT_EN, DIRECTOR_STATEMENT_ZH,
        PromptType
    )
    PROMPT_LIBRARY_AVAILABLE = True
except ImportError:
    PROMPT_LIBRARY_AVAILABLE = False
```

### Step 3: Add a new tab in the tab list

Find this line in ai_studio_elsewhere.py:

```python
tab_home, tab_new, tab_script, tab_scenes, tab_concepts, tab_exports = st.tabs([
```

Change it to:

```python
tab_home, tab_new, tab_script, tab_scenes, tab_concepts, tab_prompts, tab_exports = st.tabs([
    "🏠 Home",
    "📝 New Project",
    "📄 Script Upload",
    "🎬 Scene Breakdown",
    "🎨 Concept Images",
    "📚 Prompts Library",  # ADD THIS
    "📦 Export"
])
```

### Step 4: Add the prompt tab content

Add this **before** the `with tab_exports:` section:

```python
# ============================================================
# Tab: Prompt Library
# ============================================================

with tab_prompts:
    st.subheader("📚 Sleepless Blue Nights — Prompt Library")
    
    if not PROMPT_LIBRARY_AVAILABLE:
        st.error("❌ Prompt library not loaded")
    else:
        # Sub-tabs
        tab_prompts_list, tab_color_script, tab_director = st.tabs([
            "🎨 Prompts", "🌈 Color Script", "🎬 Director"
        ])
        
        # PROMPTS TAB
        with tab_prompts_list:
            prompt_type_filter = st.selectbox(
                "Filter by Type",
                ["All", "Concept Images", "Video Prompts", "Ink Transitions", "Locations"]
            )
            
            type_map = {
                "Concept Images": PromptType.CONCEPT_IMAGE,
                "Video Prompts": PromptType.VIDEO,
                "Ink Transitions": PromptType.INK_TRANSITION,
                "Locations": PromptType.LOCATION,
            }
            
            if prompt_type_filter == "All":
                from sleepless_blue_nights_prompt_library import (
                    CONCEPT_PROMPTS, VIDEO_PROMPTS, INK_PROMPTS, LOCATION_PROMPTS
                )
                prompts = CONCEPT_PROMPTS + VIDEO_PROMPTS + INK_PROMPTS + LOCATION_PROMPTS
            else:
                prompts = get_prompts_by_type(type_map[prompt_type_filter])
            
            for prompt in prompts:
                with st.expander(f"{prompt.title} ({prompt.type.value})"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**English:**")
                        st.text_area("", prompt.prompt_en, height=150, key=f"en_{prompt.id}", disabled=True)
                    
                    with col2:
                        st.write("**中文:**")
                        st.text_area("", prompt.prompt_zh, height=150, key=f"zh_{prompt.id}", disabled=True)
                    
                    if prompt.notes:
                        st.caption(f"📝 {prompt.notes}")
        
        # COLOR SCRIPT TAB
        with tab_color_script:
            from sleepless_blue_nights_prompt_library import Act, COLOR_SCRIPT
            
            st.write("### 🌈 Color Script")
            
            selected_act = st.selectbox(
                "Select Act",
                [Act.REUNION, Act.AFTER_REUNION, Act.SURREAL_NIGHT, Act.MORNING_AFTER]
            )
            
            frames = get_color_script_by_act(selected_act)
            
            for frame in frames:
                with st.expander(f"Scene {frame.scene_number}: {frame.scene_heading}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Primary:** {frame.primary_color}")
                        st.write(f"**Secondary:** {frame.secondary_color}")
                    with col2:
                        st.write(f"**Mood:** {frame.emotional_tone}")
                    st.write(frame.notes)
        
        # DIRECTOR'S STATEMENT TAB
        with tab_director:
            lang = st.radio("Language", ["English", "中文"], horizontal=True)
            
            if lang == "English":
                st.write(DIRECTOR_STATEMENT_EN)
            else:
                st.write(DIRECTOR_STATEMENT_ZH)
```

### Step 5: Restart the app

```bash
# Stop (Ctrl+C)
streamlit run ai_studio_elsewhere.py
```

Now you'll have a **"📚 Prompts Library"** tab in the app! 🎉

---

## Using the Prompts in Generation

### For Concept Images (with Painter Agent):

```python
from sleepless_blue_nights_prompt_library import get_prompts_by_type, PromptType

# Get a concept image prompt
prompts = get_prompts_by_type(PromptType.CONCEPT_IMAGE)
selected = prompts[0]  # Urban Night

# Use in painter_agent
concept_prompt = selected.prompt_en  # or .prompt_zh
# Pass to PainterAgent.generate_panel()
```

### For Videos (with Runway):

```python
from sleepless_blue_nights_prompt_library import get_prompts_by_type, PromptType

# Get a video prompt
video_prompts = get_prompts_by_type(PromptType.VIDEO)
runway_prompt = video_prompts[0]  # Woman Under Streetlight

# Use with motion control
from motion_control_agent import apply_motion_to_prompt
enhanced = apply_motion_to_prompt(runway_prompt.prompt_en, "Dolly-in slow")
# Pass to Runway API
```

### For Color Grading:

```python
from sleepless_blue_nights_prompt_library import get_color_script_by_act, Act

# Get color script for a scene
color_frames = get_color_script_by_act(Act.REUNION)
scene_1_colors = color_frames[0]

# Use in color grading:
# Primary: Warm Dust Orange
# Secondary: Dim Wood Brown
```

---

## Features You Now Have

### 📚 Browse All Prompts
- Filter by type (Concept, Video, Transitions, Locations)
- Bilingual (English + Chinese)
- Copy to clipboard instantly

### 🌈 View Color Script
- 13 scenes mapped to emotional journey
- Primary + secondary colors for each scene
- Design notes for each frame
- Color motif reference chart with hex codes

### 🎬 Read Director's Statement
- Festival-ready (Berlinale, Venice, TIFF, etc.)
- Bilingual versions
- Download as text file

### 🎨 Quick Integration
- Functions to get prompts by type, act, or ID
- Export prompts in JSON format for APIs
- Color motif lookup

---

## Advanced Usage

### Export a Prompt for Generation

```python
from sleepless_blue_nights_prompt_library import get_prompt_by_id, export_prompt_for_generation

# Get specific prompt
prompt = get_prompt_by_id("concept_01")

# Export with metadata
prompt_json = export_prompt_for_generation(prompt, include_metadata=True)

# Use with Painter Agent
painter_params = PainterParameters(
    subject=prompt.title,
    style=["cinematic", "poetic realism"],
    negative=["blurry", "low quality"],
)

# Generate
result = painter_agent.generate_panel(painter_params, step_index=1, step_description=prompt.prompt_en)
```

### Get All Prompts for a Specific Act

```python
from sleepless_blue_nights_prompt_library import get_prompts_by_act, Act

# Get all prompts for Act III (Surreal Night)
surreal_prompts = get_prompts_by_act(Act.SURREAL_NIGHT)

# Generate visuals for each
for prompt in surreal_prompts:
    image = painter_agent.generate_panel(..., step_description=prompt.prompt_en)
```

### Create a Color Grading Lookup

```python
from sleepless_blue_nights_prompt_library import get_color_script_by_act, Act, COLOR_MOTIFS

# For a scene in Act II
color_frames = get_color_script_by_act(Act.AFTER_REUNION)
scene_20 = color_frames[2]  # Alley Passage

# Get hex codes for grading
primary_motif = COLOR_MOTIFS["fog_white"]
secondary_motif = COLOR_MOTIFS["cobalt_blue"]

print(f"Grade with: {primary_motif.hex_code} and {secondary_motif.hex_code}")
```

---

## File Structure

After integration, your directory should look like:

```
ai-studio-elsewhere/
├── ai_studio_elsewhere.py (updated with prompt library tab)
├── agents_integration.py
├── sleepless_blue_nights_prompt_library.py (NEW)
├── sleepless_blue_nights_ui.py (NEW)
├── agents/
│   ├── painter_agent.py
│   ├── motion_control_agent.py
│   └── ... (other agents)
├── data/
└── ...
```

---

## Testing

### Test 1: Run as Standalone App

```bash
streamlit run sleepless_blue_nights_ui.py
```

You should see all prompts, color script, director's statement.

### Test 2: Run with AI Studio Elsewhere

```bash
streamlit run ai_studio_elsewhere.py
```

Look for "📚 Prompts Library" tab - click it to browse!

### Test 3: Use in Generation

```python
from sleepless_blue_nights_prompt_library import CONCEPT_PROMPTS
prompt = CONCEPT_PROMPTS[0]
print(prompt.prompt_en)  # Should print the prompt
```

---

## Next Steps

1. ✅ Copy the files
2. ✅ Integrate into AI Studio Elsewhere (or run standalone)
3. ✅ Browse prompts
4. ✅ Use prompts for concept generation
5. ✅ Wire video prompts to Runway
6. ✅ Apply color script to grading

**Everything is ready to use!** 🎬✨
