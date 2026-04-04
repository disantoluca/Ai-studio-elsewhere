#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 Scene 1 Video Generation UI
Ready-to-use prompts for Runway Gen-3 Alpha

Shows all 5 video variations + multi-angle pack
"""

import streamlit as st
from typing import Dict, Optional
import logging
import sys
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Add agents folder to path
sys.path.insert(0, str(Path(__file__).parent / "agents"))
sys.path.insert(0, str(Path.cwd() / "agents"))
sys.path.insert(0, '/mnt/user-data/outputs')

# Helper to get agent with API key
def get_agent_with_key():
    """Get RunwayVideoAgent with API key from environment"""
    try:
        from runway_video_agent import RunwayVideoAgent
        api_key = os.getenv("RUNWAY_API_KEY")
        if api_key:
            return RunwayVideoAgent(api_key=api_key)
        else:
            logger.warning("⚠️ RUNWAY_API_KEY not found in environment")
            return None
    except Exception as e:
        logger.error(f"❌ Failed to create agent: {e}")
        return None

# Try multiple import strategies
SCENE_1_AVAILABLE = False
RUNWAY_AVAILABLE = False

# Strategy 1: Direct import
try:
    from scene_1_prompts import (
        SCENE_1_METADATA,
        get_all_scene_1_videos,
        get_scene_1_multi_angles,
        format_runway_prompt
    )
    SCENE_1_AVAILABLE = True
    logger.info("✅ Scene 1 prompts loaded")
except ImportError as e:
    logger.warning(f"⚠️ Scene 1 prompts not available: {e}")
    SCENE_1_AVAILABLE = False

# Try runway agent (check agents folder first, then current dir)
try:
    from runway_video_agent import RunwayVideoAgent, VideoGenRequest
    RUNWAY_AVAILABLE = True
    logger.info("✅ Runway agent module loaded")
except ImportError:
    try:
        # Try from agents subfolder
        from agents.runway_video_agent import RunwayVideoAgent, VideoGenRequest
        RUNWAY_AVAILABLE = True
        logger.info("✅ Runway agent loaded from agents/")
    except ImportError as e:
        logger.warning(f"⚠️ Runway agent not available: {e}")
        RUNWAY_AVAILABLE = False

def display_scene_1_video_generation():
    """Main Scene 1 video generation interface"""
    
    if not SCENE_1_AVAILABLE:
        st.error("❌ Scene 1 prompts not found")
        st.info("Make sure scene_1_prompts.py is in the same directory")
        return
    
    if not RUNWAY_AVAILABLE:
        st.error("❌ Runway agent not found")
        st.info("Make sure runway_video_agent.py is in the same directory")
        return
    
    st.header("🎬 Scene 1 - Opening Banquet Hall")
    st.subheader("Runway Gen-3 Alpha Video Generation")
    
    # Scene metadata
    metadata = SCENE_1_METADATA
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Scene", metadata["scene_number"])
    with col2:
        st.metric("Location", "Banquet Hall")
    with col3:
        st.metric("Time", "Evening")
    with col4:
        st.metric("Mood", "Nostalgic")
    
    st.write(f"**Location:** {metadata['location']}")
    st.write(f"**Color Scheme:** {metadata['color_scheme']}")
    st.write(f"**Visual Reference:** {metadata['visual_reference']}")
    
    st.markdown("---")
    
    # Tabs for different generation modes
    tab_individual, tab_multi_angle, tab_batch = st.tabs([
        "🎥 Individual Shots",
        "🔄 Multi-Angle",
        "📹 Generate All"
    ])
    
    # ============================================================
    # TAB 1: INDIVIDUAL SHOTS
    # ============================================================
    
    with tab_individual:
        st.subheader("🎥 Individual Scene 1 Shots")
        
        shots = get_all_scene_1_videos()
        shot_names = list(shots.keys())
        
        # Shot selector
        selected_shot_name = st.selectbox(
            "Select shot type",
            shot_names,
            format_func=lambda x: f"{x.replace('_', ' ').title()} Shot"
        )
        
        shot = shots[selected_shot_name]
        
        # Display shot details
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Duration", f"{shot['duration']}s")
        with col2:
            st.metric("Motion", shot['motion'].replace('_', ' ').title())
        with col3:
            st.metric("Style", shot['style'].title())
        
        # English prompt
        st.write("**English Prompt:**")
        st.text_area("Prompt (English)", shot['prompt_en'], height=120, disabled=True)
        
        # Chinese prompt
        st.write("**Chinese Prompt:**")
        st.text_area("Prompt (中文)", shot['prompt_zh'], height=120, disabled=True)
        
        # Motion description
        st.write("**Camera Motion:**")
        st.info(shot['motion_description'])
        
        # Notes
        if 'notes' in shot:
            st.write("**Director's Notes:**")
            st.info(shot['notes'])
        
        # Generate button
        if st.button("🎥 Generate This Shot", type="primary", use_container_width=True):
            with st.spinner(f"⏳ Generating {selected_shot_name} shot..."):
                # Create video request
                request = VideoGenRequest(
                    scene_id=shot['id'],
                    scene_heading=f"Scene 1 - {selected_shot_name.replace('_', ' ').title()}",
                    prompt_en=shot['prompt_en'],
                    prompt_zh=shot['prompt_zh'],
                    motion_type=shot['motion'],
                    style=shot['style'],
                    duration=shot['duration'],
                    notes=shot.get('notes', '')
                )
                
                # Generate
                agent = get_agent_with_key()
                result = agent.generate_video(request)
                
                st.success(f"✅ Queued: {shot['id']}")
                st.metric("Status", result.status)
                st.info(f"📹 Video URL: {result.video_url}")
    
    # ============================================================
    # TAB 2: MULTI-ANGLE
    # ============================================================
    
    with tab_multi_angle:
        st.subheader("🔄 Scene 1 - Multi-Angle Variations")
        
        st.write("Generate the same scene from 6 different camera angles")
        
        angles = get_scene_1_multi_angles()
        
        # Display all angles
        cols = st.columns(2)
        
        for i, (angle_key, angle_data) in enumerate(angles.items()):
            with cols[i % 2]:
                st.write(f"### 📹 {angle_key.replace('_', ' ').title()}")
                st.write(f"**Angle:** {angle_data['angle'].title()}")
                st.text_area(
                    f"{angle_key}_prompt",
                    angle_data['prompt_en'],
                    height=80,
                    disabled=True,
                    label_visibility="collapsed"
                )
                
                if st.button(f"Generate {angle_key.replace('_', ' ')}", key=f"angle_{angle_key}"):
                    with st.spinner(f"⏳ Generating {angle_key}..."):
                        request = VideoGenRequest(
                            scene_id=f"scene_1_{angle_key}",
                            scene_heading=f"Scene 1 - {angle_key.replace('_', ' ').title()}",
                            prompt_en=angle_data['prompt_en'],
                            prompt_zh=angle_data['prompt_zh'],
                            motion_type="static",
                            style="cinematic",
                            duration=6
                        )
                        
                        agent = get_agent_with_key()
                        result = agent.generate_video(request)
                        
                        st.success(f"✅ Queued: {angle_key}")
        
        st.markdown("---")
        
        # Generate all angles button
        if st.button("🔄 Generate ALL Angles at Once", type="primary", use_container_width=True):
            with st.spinner("⏳ Generating 6 angle variations..."):
                results = []
                
                for angle_key, angle_data in angles.items():
                    request = VideoGenRequest(
                        scene_id=f"scene_1_{angle_key}",
                        scene_heading=f"Scene 1 - {angle_key.replace('_', ' ').title()}",
                        prompt_en=angle_data['prompt_en'],
                        prompt_zh=angle_data['prompt_zh'],
                        motion_type="static",
                        style="cinematic",
                        duration=6
                    )
                    
                    agent = get_agent_with_key()
                    result = agent.generate_video(request)
                    results.append(result)
                
                st.success(f"✅ Queued {len(results)} angle variations")
                
                # Show results table
                result_data = []
                for result in results:
                    result_data.append({
                        "Angle": result.scene_id.split("_")[-1].replace("_", " ").title(),
                        "Status": result.status,
                        "Duration": f"{result.duration}s"
                    })
                
                st.dataframe(result_data, use_container_width=True)
    
    # ============================================================
    # TAB 3: GENERATE ALL
    # ============================================================
    
    with tab_batch:
        st.subheader("📹 Generate Complete Scene 1 Pack")
        
        st.write("Generate all 5 shots + 6 angles (11 videos total)")
        
        all_shots = get_all_scene_1_videos()
        total_videos = len(all_shots) + len(get_scene_1_multi_angles())
        total_duration = sum(shot['duration'] for shot in all_shots.values()) + (6 * 6)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Videos", total_videos)
        with col2:
            st.metric("Total Duration", f"{total_duration}s")
        with col3:
            st.metric("Estimated Time", "~15-20 min")
        
        st.warning("⚠️ This will generate 11 videos. Make sure you have enough API quota!")
        
        if st.button("📹 Generate Complete Pack", type="primary", use_container_width=True):
            with st.spinner(f"⏳ Generating {total_videos} videos..."):
                results = []
                progress_bar = st.progress(0)
                
                # Generate individual shots
                for i, (shot_name, shot) in enumerate(all_shots.items()):
                    request = VideoGenRequest(
                        scene_id=shot['id'],
                        scene_heading=f"Scene 1 - {shot_name.replace('_', ' ').title()}",
                        prompt_en=shot['prompt_en'],
                        prompt_zh=shot['prompt_zh'],
                        motion_type=shot['motion'],
                        style=shot['style'],
                        duration=shot['duration']
                    )
                    
                    agent = get_agent_with_key()
                    result = agent.generate_video(request)
                    results.append(result)
                    
                    progress_bar.progress((i + 1) / total_videos)
                
                # Generate multi-angles
                angles = get_scene_1_multi_angles()
                for i, (angle_key, angle_data) in enumerate(angles.items()):
                    request = VideoGenRequest(
                        scene_id=f"scene_1_{angle_key}",
                        scene_heading=f"Scene 1 - {angle_key.replace('_', ' ').title()}",
                        prompt_en=angle_data['prompt_en'],
                        prompt_zh=angle_data['prompt_zh'],
                        motion_type="static",
                        style="cinematic",
                        duration=6
                    )
                    
                    agent = get_agent_with_key()
                    result = agent.generate_video(request)
                    results.append(result)
                    
                    progress_bar.progress((len(all_shots) + i + 1) / total_videos)
                
                st.success(f"✅ Queued {total_videos} videos!")
                
                # Show summary
                st.write("**Generation Summary:**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Individual Shots", len(all_shots))
                with col2:
                    st.metric("Multi-Angles", len(angles))
                with col3:
                    st.metric("Total Queued", total_videos)

if __name__ == "__main__":
    st.set_page_config(page_title="Scene 1 Video Generation", layout="wide")
    display_scene_1_video_generation()
