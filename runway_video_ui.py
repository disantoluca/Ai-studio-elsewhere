#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎥 Runway Video Generation UI Component
For AI Studio Elsewhere - Beautiful video generation interface

Integrates with runway_video_agent.py
"""

import streamlit as st
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
# STREAMLIT UI COMPONENTS
# ============================================================

def display_video_generation_tab(scenes: List[Dict], project_title: str):
    """
    Main video generation interface
    
    Args:
        scenes: List of scene data dicts
        project_title: Project title for context
    """
    
    if not RUNWAY_AVAILABLE:
        st.error("❌ Runway Video Agent not loaded")
        return
    
    st.header("🎥 Video Generation with Runway Gen-3")
    
    if not scenes:
        st.warning("⚠️ No scenes available. Extract scenes first.")
        return
    
    agent = get_runway_agent()
    
    if not agent.available:
        st.warning("⚠️ Runway API not configured. Add RUNWAY_API_KEY to .env")
        return
    
    # Tabs for different generation modes
    tab_single, tab_multi_angle, tab_batch = st.tabs([
        "🎬 Single Scene",
        "🔄 Multi-Angle",
        "📹 Batch Generation"
    ])
    
    # ============================================================
    # TAB 1: SINGLE SCENE GENERATION
    # ============================================================
    
    with tab_single:
        st.subheader("🎬 Generate Video for Single Scene")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Scene selector
            scene_options = {
                f"Scene {i+1}: {s.get('heading', 'Untitled')}": i 
                for i, s in enumerate(scenes)
            }
            selected_scene_label = st.selectbox(
                "Select Scene",
                list(scene_options.keys())
            )
            selected_scene_idx = scene_options[selected_scene_label]
            scene = scenes[selected_scene_idx]
        
        with col2:
            # Motion control
            motion_options = agent.get_motion_options()
            selected_motion = st.selectbox(
                "Camera Motion",
                list(motion_options.keys()),
                format_func=lambda x: f"{x.replace('_', ' ').title()} - {motion_options[x]}"
            )
        
        # Style selection
        col1, col2 = st.columns(2)
        
        with col1:
            style_options = agent.get_style_options()
            selected_style = st.selectbox(
                "Visual Style",
                list(style_options.keys()),
                format_func=lambda x: f"{x.title()}"
            )
        
        with col2:
            duration = st.slider("Duration (seconds)", 5, 30, 8, step=1)
        
        # Display selected prompt
        st.write("**Scene Prompt:**")
        prompt = scene.get("prompt", "")
        st.text_area("Prompt (read-only)", prompt, height=150, disabled=True)
        
        # Generation button
        if st.button("🎥 Generate Video", type="primary", use_container_width=True):
            with st.spinner("⏳ Generating video (this may take a minute)..."):
                request = VideoGenRequest(
                    scene_id=scene.get("id", f"scene_{selected_scene_idx}"),
                    scene_heading=scene.get("heading", "Scene"),
                    prompt_en=prompt,
                    motion_type=selected_motion,
                    style=selected_style,
                    duration=duration,
                    notes=f"Generated for {project_title}"
                )
                
                result = agent.generate_video(request)
                
                # Display result
                st.success(f"✅ Video generation queued: {result.scene_id}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Status", result.status)
                with col2:
                    st.metric("Motion", selected_motion.replace("_", " ").title())
                with col3:
                    st.metric("Duration", f"{result.duration}s")
                
                # Show metadata
                st.write("**Generation Details:**")
                st.json(result.metadata or {})
                
                # Video placeholder (would show actual video URL)
                st.info("📹 Video will be available at: " + result.video_url)
    
    # ============================================================
    # TAB 2: MULTI-ANGLE GENERATION
    # ============================================================
    
    with tab_multi_angle:
        st.subheader("🔄 Generate Multi-Angle Videos")
        
        st.write("Generate the same scene from multiple camera angles")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Scene selector
            scene_options = {
                f"Scene {i+1}: {s.get('heading', 'Untitled')}": i 
                for i, s in enumerate(scenes)
            }
            selected_scene_label = st.selectbox(
                "Select Scene",
                list(scene_options.keys()),
                key="multi_angle_scene"
            )
            selected_scene_idx = scene_options[selected_scene_label]
            scene = scenes[selected_scene_idx]
        
        with col2:
            # Style for all angles
            style_options = agent.get_style_options()
            selected_style = st.selectbox(
                "Visual Style (for all angles)",
                list(style_options.keys()),
                key="multi_angle_style"
            )
        
        # Angle selection
        st.write("**Select Angles to Generate:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            gen_wide = st.checkbox("📹 Wide Shot", value=True)
        with col2:
            gen_medium = st.checkbox("📹 Medium Shot", value=True)
        with col3:
            gen_close = st.checkbox("📹 Close-up", value=True)
        
        angles = []
        if gen_wide:
            angles.append("wide")
        if gen_medium:
            angles.append("medium")
        if gen_close:
            angles.append("close")
        
        # Generation button
        if st.button("🔄 Generate All Angles", type="primary", use_container_width=True):
            with st.spinner(f"⏳ Generating {len(angles)} angle variations..."):
                results = agent.generate_multi_angle_videos(scene, angles)
                
                st.success(f"✅ Generated {len(results)} angle variations")
                
                # Display results
                cols = st.columns(len(results))
                for i, (angle, result) in enumerate(results.items()):
                    with cols[i]:
                        st.write(f"### {angle.upper()}")
                        st.metric("Status", result.status)
                        st.metric("Scene ID", result.scene_id.split("__")[1])
                        if st.button(f"📹 Watch {angle}", key=f"watch_{angle}"):
                            st.info(f"Video: {result.video_url}")
    
    # ============================================================
    # TAB 3: BATCH GENERATION
    # ============================================================
    
    with tab_batch:
        st.subheader("📹 Batch Video Generation")
        
        st.write("Generate videos for multiple scenes at once with consistent styling")
        
        # Motion sequence
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Motion Sequence (cycles through selected scenes):**")
            motion_options = agent.get_motion_options()
            
            selected_motions = st.multiselect(
                "Select motion types",
                list(motion_options.keys()),
                default=["dolly_in", "pan_left", "static"],
                format_func=lambda x: f"{x.replace('_', ' ').title()} - {motion_options[x]}"
            )
        
        with col2:
            # Style
            style_options = agent.get_style_options()
            selected_style = st.selectbox(
                "Visual Style (for all)",
                list(style_options.keys()),
                key="batch_style"
            )
        
        # Scene selection for batch
        st.write("**Select Scenes for Batch Generation:**")
        
        scene_selection = st.multiselect(
            "Scenes to generate",
            [f"Scene {i+1}: {s.get('heading', 'Untitled')}" for i, s in enumerate(scenes)],
            default=[f"Scene 1: {scenes[0].get('heading', 'Untitled')}"]
        )
        
        # Extract selected scene indices
        selected_indices = []
        for selection in scene_selection:
            scene_num = int(selection.split(":")[0].replace("Scene ", "")) - 1
            selected_indices.append(scene_num)
        
        # Batch generation button
        if st.button("📹 Generate Batch", type="primary", use_container_width=True):
            if not selected_motions:
                st.warning("Select at least one motion type")
            else:
                selected_scenes = [scenes[i] for i in selected_indices]
                
                with st.spinner(f"⏳ Generating videos for {len(selected_scenes)} scenes..."):
                    results = agent.generate_videos_for_scenes(
                        selected_scenes,
                        motion_types=selected_motions,
                        style=selected_style
                    )
                    
                    st.success(f"✅ Queued {len(results)} videos for generation")
                    
                    # Display results as table
                    result_data = []
                    for result in results:
                        result_data.append({
                            "Scene": result.scene_id,
                            "Status": result.status,
                            "Motion": result.motion_applied or "None",
                            "Duration": f"{result.duration}s"
                        })
                    
                    st.dataframe(result_data, use_container_width=True)
                    
                    # Statistics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Videos", len(results))
                    with col2:
                        st.metric("Total Duration", f"{len(results) * 8}s")
                    with col3:
                        st.metric("Status", "Generating")
    
    # ============================================================
    # GENERATION HISTORY
    # ============================================================
    
    st.markdown("---")
    st.subheader("📊 Generation History")
    
    history = agent.get_generation_history()
    
    if history:
        history_data = []
        for item in history[-10:]:  # Last 10
            history_data.append({
                "Scene": item["scene_id"],
                "Prompt": item["prompt_used"][:50] + "...",
                "Motion": item["motion_applied"] or "static",
                "Status": item["status"],
                "Time": item["timestamp"]
            })
        
        st.dataframe(history_data, use_container_width=True)
    else:
        st.info("No videos generated yet")
    
    # Agent status
    status = agent.get_status()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Videos Generated", status["videos_generated"])
    with col2:
        st.metric("Motion Types", len(status["motion_options"]))
    with col3:
        st.metric("Style Presets", len(status["style_options"]))

def display_video_widget_sidebar() -> Optional[Dict]:
    """Compact video generation widget for sidebar"""
    
    if not RUNWAY_AVAILABLE:
        return None
    
    agent = get_runway_agent()
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎥 Quick Video Gen")
    
    motion_options = agent.get_motion_options()
    selected_motion = st.sidebar.selectbox(
        "Motion",
        list(motion_options.keys()),
        format_func=lambda x: x.replace("_", " ").title()
    )
    
    duration = st.sidebar.slider("Duration", 5, 20, 8)
    
    if st.sidebar.button("🎥 Generate", use_container_width=True):
        return {
            "motion": selected_motion,
            "duration": duration
        }
    
    return None

if __name__ == "__main__":
    # Standalone demo
    st.set_page_config(page_title="Video Generation", layout="wide")
    
    # Mock scenes for demo
    demo_scenes = [
        {
            "id": "scene_01",
            "heading": "INT. SHANGHAI ALLEY - NIGHT",
            "prompt": "Shanghai street at 2am, neon reflections on wet pavement, deep cobalt-blue tones, diffused fog, soft cinematic grain, poetic realism, empty sidewalks, emotional silence."
        },
        {
            "id": "scene_02",
            "heading": "EXT. ROOFTOP - NIGHT",
            "prompt": "Shanghai rooftop at night, distant neon glow, cityscape, soft moonlight, intimate atmosphere, two figures standing apart, unresolved tension."
        }
    ]
    
    display_video_generation_tab(demo_scenes, "Sleepless Blue Nights")
