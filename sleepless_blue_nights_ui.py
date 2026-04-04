#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit UI Components for Sleepless Blue Nights Prompt Library
Integrates with ai_studio_elsewhere.py for easy prompt access and generation
"""

import streamlit as st
from pathlib import Path
import sys

# Add current directory to path to import prompt library
sys.path.insert(0, str(Path(__file__).parent))

try:
    from sleepless_blue_nights_prompt_library import (
        CONCEPT_PROMPTS, VIDEO_PROMPTS, INK_PROMPTS, LOCATION_PROMPTS, ACTOR_PROMPTS,
        COLOR_SCRIPT, COLOR_MOTIFS,
        DIRECTOR_STATEMENT_EN, DIRECTOR_STATEMENT_ZH,
        Act, PromptType,
        get_prompts_by_type, get_prompts_by_act, get_color_script_by_act,
        get_library_stats, export_prompt_for_generation
    )
    LIBRARY_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Prompt library not available: {e}")
    LIBRARY_AVAILABLE = False

# ============================================================
# STREAMLIT COMPONENTS
# ============================================================

def display_prompt_library():
    """Main prompt library interface"""
    
    if not LIBRARY_AVAILABLE:
        st.error("❌ Prompt library not loaded. Make sure sleepless_blue_nights_prompt_library.py is in the same directory.")
        return
    
    st.header("📚 Sleepless Blue Nights — Complete Prompt Library")
    
    # Tabs for different sections
    tab_prompts, tab_color_script, tab_director, tab_library_stats = st.tabs([
        "🎨 Prompts",
        "🌈 Color Script",
        "🎬 Director's Statement",
        "📊 Library Stats"
    ])
    
    # ============================================================
    # TAB 1: PROMPTS
    # ============================================================
    
    with tab_prompts:
        st.subheader("🎨 Visual Prompts for Generation")
        
        # Sidebar filters
        col1, col2 = st.columns(2)
        
        with col1:
            prompt_type = st.selectbox(
                "Filter by Type",
                ["All", "Concept Images", "Video Prompts", "Ink Transitions", "Locations", "Actor Consistency"]
            )
        
        with col2:
            language = st.radio("Language", ["English", "Chinese"], horizontal=True)
        
        # Map selection to PromptType
        type_map = {
            "Concept Images": PromptType.CONCEPT_IMAGE,
            "Video Prompts": PromptType.VIDEO,
            "Ink Transitions": PromptType.INK_TRANSITION,
            "Locations": PromptType.LOCATION,
            "Actor Consistency": PromptType.ACTOR_CONSISTENCY,
        }
        
        # Get prompts
        if prompt_type == "All":
            all_prompts = CONCEPT_PROMPTS + VIDEO_PROMPTS + INK_PROMPTS + LOCATION_PROMPTS + ACTOR_PROMPTS
        else:
            all_prompts = get_prompts_by_type(type_map[prompt_type])
        
        # Display prompts
        for prompt in all_prompts:
            with st.expander(f"**{prompt.title}** ({prompt.type.value})"):
                st.write("**English:**")
                st.write(prompt.prompt_en)
                
                st.write("\n**中文:**")
                st.write(prompt.prompt_zh)
                
                # Metadata
                col1, col2, col3 = st.columns(3)
                with col1:
                    if prompt.scene_number:
                        st.info(f"Scene {prompt.scene_number}")
                with col2:
                    if prompt.act:
                        st.info(f"{prompt.act.value}")
                with col3:
                    if prompt.color_motifs:
                        st.info(f"Colors: {', '.join(prompt.color_motifs)}")
                
                if prompt.notes:
                    st.caption(f"📝 {prompt.notes}")
                
                # Copy to clipboard button
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(f"📋 Copy EN", key=f"copy_en_{prompt.id}"):
                        st.write(f"```\n{prompt.prompt_en}\n```")
                        st.success("Copied!")
                with col2:
                    if st.button(f"📋 Copy ZH", key=f"copy_zh_{prompt.id}"):
                        st.write(f"```\n{prompt.prompt_zh}\n```")
                        st.success("Copied!")
                with col3:
                    if st.button(f"🎨 Use for Generation", key=f"use_{prompt.id}"):
                        st.session_state.selected_prompt = prompt
                        st.success(f"Selected: {prompt.title}")
    
    # ============================================================
    # TAB 2: COLOR SCRIPT
    # ============================================================
    
    with tab_color_script:
        st.subheader("🌈 Color Script — Emotional Journey")
        
        # Filter by act
        selected_act = st.selectbox(
            "Select Act",
            [Act.REUNION, Act.AFTER_REUNION, Act.SURREAL_NIGHT, Act.MORNING_AFTER]
        )
        
        # Display color script
        frames = get_color_script_by_act(selected_act)
        
        st.write(f"## {selected_act.value}")
        
        for frame in frames:
            with st.expander(f"Scene {frame.scene_number}: {frame.scene_heading}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Primary Color:** {frame.primary_color}")
                    st.write(f"**Secondary Color:** {frame.secondary_color}")
                
                with col2:
                    st.write(f"**Emotional Tone:** {frame.emotional_tone}")
                
                st.write("**Notes:**")
                st.write(frame.notes)
        
        # Color motif reference
        st.markdown("---")
        st.subheader("🎨 Color Motif Reference")
        
        cols = st.columns(3)
        col_idx = 0
        
        for motif_id, motif in COLOR_MOTIFS.items():
            with cols[col_idx % 3]:
                st.write(f"### {motif.name}")
                st.color_picker(f"Color:", value=motif.hex_code, disabled=True, key=f"color_{motif_id}")
                st.write(f"**EN:** {motif.emotional_meaning_en}")
                st.write(f"**ZH:** {motif.emotional_meaning_zh}")
            col_idx += 1
    
    # ============================================================
    # TAB 3: DIRECTOR'S STATEMENT
    # ============================================================
    
    with tab_director:
        st.subheader("🎬 Director's Statement")
        
        statement_lang = st.radio("Language", ["English", "中文"], horizontal=True)
        
        if statement_lang == "English":
            st.write(DIRECTOR_STATEMENT_EN)
        else:
            st.write(DIRECTOR_STATEMENT_ZH)
        
        # Download button
        if statement_lang == "English":
            st.download_button(
                label="📥 Download Director's Statement (EN)",
                data=DIRECTOR_STATEMENT_EN,
                file_name="sleepless_blue_nights_directors_statement_en.txt",
                mime="text/plain"
            )
        else:
            st.download_button(
                label="📥 Download Director's Statement (ZH)",
                data=DIRECTOR_STATEMENT_ZH,
                file_name="sleepless_blue_nights_directors_statement_zh.txt",
                mime="text/plain"
            )
    
    # ============================================================
    # TAB 4: LIBRARY STATS
    # ============================================================
    
    with tab_library_stats:
        st.subheader("📊 Library Statistics")
        
        stats = get_library_stats()
        
        # Display as metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Prompts", stats["total_prompts"])
        with col2:
            st.metric("Color Frames", stats["color_frames"])
        with col3:
            st.metric("Color Motifs", stats["color_motifs"])
        
        # Breakdown
        st.subheader("Prompt Breakdown")
        
        breakdown_data = {
            "Concept Images": stats["concept_images"],
            "Video Prompts": stats["video_prompts"],
            "Ink Transitions": stats["ink_transitions"],
            "Locations": stats["locations"],
            "Actor Consistency": stats["actor_consistency"],
        }
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Prompt Types:**")
            for ptype, count in breakdown_data.items():
                st.write(f"• {ptype}: {count}")
        
        with col2:
            # Bar chart
            import pandas as pd
            df = pd.DataFrame(list(breakdown_data.items()), columns=["Type", "Count"])
            st.bar_chart(df.set_index("Type"))

def display_prompt_selector_widget():
    """Compact widget for selecting a prompt to use"""
    
    if not LIBRARY_AVAILABLE:
        return None
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎨 Quick Prompt Selector")
    
    prompt_type = st.sidebar.selectbox(
        "Prompt Type",
        ["Concept Image", "Video", "Ink Transition", "Location"]
    )
    
    type_map = {
        "Concept Image": CONCEPT_PROMPTS,
        "Video": VIDEO_PROMPTS,
        "Ink Transition": INK_PROMPTS,
        "Location": LOCATION_PROMPTS,
    }
    
    prompts = type_map.get(prompt_type, [])
    
    if prompts:
        selected_prompt = st.sidebar.selectbox(
            "Select Prompt",
            [p.title for p in prompts]
        )
        
        # Find the prompt
        for p in prompts:
            if p.title == selected_prompt:
                st.sidebar.write(f"**Selected:** {p.title}")
                
                if st.sidebar.button("📋 Copy English"):
                    st.sidebar.code(p.prompt_en, language="text")
                
                if st.sidebar.button("📋 Copy Chinese"):
                    st.sidebar.code(p.prompt_zh, language="text")
                
                return p
    
    return None

# ============================================================
# INTEGRATION HELPER
# ============================================================

def get_selected_prompt():
    """Get the currently selected prompt from session state"""
    return st.session_state.get("selected_prompt", None)

def set_selected_prompt(prompt):
    """Set the selected prompt in session state"""
    st.session_state.selected_prompt = prompt

if __name__ == "__main__":
    # Standalone demo
    st.set_page_config(page_title="Sleepless Blue Nights Prompt Library", layout="wide")
    display_prompt_library()
