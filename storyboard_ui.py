#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 Storyboard UI Components for AI Studio Elsewhere
Streamlit integration for interactive storyboard generation and display
"""

import streamlit as st
from typing import Dict, Any, Callable, Optional


def display_storyboard_ui(
    scene: Dict[str, Any],
    generate_image_func: Callable,
    title: str = "🎬 Storyboard"
):
    """
    Display storyboard generation UI in Streamlit
    
    Args:
        scene: Scene dict with location, visual_prompt, video_prompt
        generate_image_func: Function to generate images (must return PIL Image or tuple)
        title: UI section title
    """
    
    from storyboard_generator import generate_storyboard, get_storyboard_layouts
    
    st.markdown(f"## {title}")
    st.caption("Cinematic structure from scene idea")
    
    # Layout selector
    col1, col2 = st.columns([3, 1])
    
    with col1:
        layout_options = get_storyboard_layouts()
        selected_layout = st.selectbox(
            "🎞 Storyboard Layout",
            list(layout_options.keys()),
            index=0
        )
        panel_count = layout_options[selected_layout]
    
    with col2:
        if st.button("🧩 Generate", use_container_width=True):
            st.session_state.generate_storyboard = True
    
    # Generate storyboard
    if st.session_state.get("generate_storyboard", False):
        
        storyboard = generate_storyboard(scene, panel_count)
        
        st.success(f"✅ Generated {len(storyboard.panels)} panels")
        
        # Determine columns based on layout
        if panel_count == 6 or panel_count == 12:
            num_cols = 3
        else:  # 8 panels
            num_cols = 2
        
        cols = st.columns(num_cols)
        
        # Display each panel
        for i, panel in enumerate(storyboard.panels):
            col = cols[i % num_cols]
            
            with col:
                # Panel header
                st.markdown(f"### {i+1}. {panel.shot}")
                st.caption(panel.description)
                
                # Generate and display image
                with st.spinner(f"🎨 Rendering panel {i+1}..."):
                    try:
                        image = generate_image_func(panel.prompt)
                        
                        # Handle different return types
                        if isinstance(image, tuple):
                            # Error case
                            st.warning(image[1])
                        elif image is not None:
                            st.image(image, use_container_width=True)
                        else:
                            st.info("⚠️ No image generated")
                    
                    except Exception as e:
                        st.warning(f"⚠️ Image generation error: {str(e)[:50]}")
                
                # Collapsible prompt
                with st.expander("📝 Prompt"):
                    st.code(panel.prompt, language="text")
                
                # Camera notes
                if panel.camera_direction:
                    st.caption(f"📹 {panel.camera_direction}")
                
                st.divider()
        
        # Export options
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📋 Copy All Prompts"):
                all_prompts = "\n\n".join([
                    f"{i+1}. {p.shot}\n{p.prompt}" 
                    for i, p in enumerate(storyboard.panels)
                ])
                st.code(all_prompts, language="text")
                st.success("✅ Copied!")
        
        with col2:
            if st.button("📊 Export as JSON"):
                import json
                export_data = {
                    "scene": scene.get("scene_number", "Scene"),
                    "layout": f"{panel_count} panels",
                    "panels": [
                        {
                            "number": i+1,
                            "shot": p.shot,
                            "description": p.description,
                            "prompt": p.prompt,
                            "camera_direction": p.camera_direction
                        }
                        for i, p in enumerate(storyboard.panels)
                    ]
                }
                st.json(export_data)
        
        with col3:
            if st.button("🎬 Clear Storyboard"):
                st.session_state.generate_storyboard = False
                st.rerun()


def display_storyboard_compact(
    panel_count: int = 6,
    title: str = "Quick Storyboard"
):
    """
    Compact storyboard display (sidebar or minimal view)
    
    Args:
        panel_count: Number of panels
        title: Display title
    """
    st.subheader(f"🎞 {title}")
    
    from storyboard_generator import get_storyboard_layouts
    
    layouts = get_storyboard_layouts()
    selected = st.selectbox("Format", list(layouts.keys()))
    
    return layouts[selected]


def create_storyboard_template(scene_type: str) -> Dict[str, Any]:
    """
    Create storyboard template for common scene types
    
    Args:
        scene_type: Type of scene (dialogue, action, transition, etc.)
    
    Returns:
        Template dict
    """
    
    templates = {
        "dialogue": {
            "location": "interior setting",
            "visual_prompt": "intimate character dialogue, realistic lighting",
            "video_prompt": "subtle camera movement, emotional beats",
            "duration": 20
        },
        "action": {
            "location": "dynamic environment",
            "visual_prompt": "kinetic action scene, dramatic lighting",
            "video_prompt": "fast paced movement, intense motion control",
            "duration": 30
        },
        "transition": {
            "location": "transitional space",
            "visual_prompt": "cinematic transition, atmospheric",
            "video_prompt": "smooth dissolve, ink bloom transition",
            "duration": 5
        },
        "establishing": {
            "location": "wide environment",
            "visual_prompt": "epic establishing shot, location showcase",
            "video_prompt": "grand camera movement, cinematic scale",
            "duration": 15
        },
        "montage": {
            "location": "multiple locations",
            "visual_prompt": "fast montage elements, varied locations",
            "video_prompt": "rapid cuts, rhythmic transitions",
            "duration": 60
        }
    }
    
    return templates.get(scene_type, templates["dialogue"])
