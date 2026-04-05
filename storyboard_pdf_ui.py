#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 Storyboard PDF Export UI — Streamlit Integration
Director-ready PDF export from Streamlit
"""

import streamlit as st
import os
from pathlib import Path
from typing import List, Dict, Any, Optional


def display_pdf_export_ui(
    storyboard: List[Dict[str, Any]],
    image_paths: List[Optional[str]],
    title: str = "Storyboard",
    director: str = "",
    scene_number: str = "",
    project_name: str = ""
):
    """
    Display PDF export controls in Streamlit
    
    Args:
        storyboard: List of panel dicts
        image_paths: List of image file paths
        title: PDF title
        director: Director name
        scene_number: Scene identifier
        project_name: Project name
    """
    
    st.markdown("---")
    st.subheader("📄 Export to PDF")
    
    # Export button
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        export_button = st.button("🎬 Generate PDF Storyboard", use_container_width=True)
    
    with col2:
        # Optional: Include notes in PDF
        include_prompts = st.checkbox("Include technical prompts", value=True)
    
    with col3:
        # Quality selector
        quality = st.selectbox("Quality", ["Standard", "High"], index=0)
    
    # Generate PDF
    if export_button:
        with st.spinner("🎨 Generating PDF..."):
            try:
                from storyboard_pdf_export import export_storyboard_pdf
                
                # Clean up image paths (ensure they exist)
                valid_image_paths = []
                for path in image_paths:
                    if path and os.path.exists(path):
                        valid_image_paths.append(path)
                    else:
                        valid_image_paths.append(None)
                
                # Generate PDF
                pdf_path = export_storyboard_pdf(
                    storyboard=storyboard,
                    image_paths=valid_image_paths,
                    title=title,
                    director=director,
                    scene_number=scene_number,
                    project_name=project_name,
                    output_dir="exports"
                )
                
                if pdf_path and os.path.exists(pdf_path):
                    
                    # Read PDF
                    with open(pdf_path, "rb") as pdf_file:
                        pdf_data = pdf_file.read()
                    
                    # Generate filename
                    filename = Path(pdf_path).name
                    
                    # Download button
                    st.download_button(
                        label="📥 Download PDF",
                        data=pdf_data,
                        file_name=filename,
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    st.success(f"✅ PDF ready: {filename}")
                    st.caption(f"📊 Panels: {len(storyboard)} | File size: {len(pdf_data)/1024:.1f} KB")
                
                else:
                    st.error("❌ PDF generation failed")
            
            except ImportError:
                st.error("❌ reportlab not installed. Run: pip install reportlab")
            
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")


def display_storyboard_info(storyboard: List[Dict[str, Any]]):
    """Display storyboard statistics and info"""
    
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Panels", len(storyboard))
    
    with col2:
        shots = [p.get('shot', '') for p in storyboard]
        st.metric("Unique Shots", len(set(shots)))
    
    with col3:
        descriptions = [p.get('description', '') for p in storyboard]
        avg_desc_len = sum(len(d) for d in descriptions) // len(descriptions) if descriptions else 0
        st.metric("Avg Description", f"{avg_desc_len} chars")
    
    with col4:
        st.metric("Format", "6/8/12 panel")
    
    # Panel breakdown
    with st.expander("📋 Panel Breakdown"):
        for i, panel in enumerate(storyboard):
            with st.container():
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.caption(f"**Panel {i+1}**")
                with col2:
                    st.caption(f"{panel.get('shot', 'Shot')} — {panel.get('description', '')[:50]}...")


def create_pdf_export_settings() -> Dict[str, Any]:
    """Create sidebar settings for PDF export"""
    
    with st.sidebar:
        st.markdown("---")
        st.subheader("⚙️ PDF Settings")
        
        project_name = st.text_input("Project Name", value="Untitled Project")
        director_name = st.text_input("Director Name", value="")
        scene_id = st.text_input("Scene Number", value="01")
        
        include_metadata = st.checkbox("Include metadata", value=True)
        include_timestamps = st.checkbox("Include timestamps", value=True)
        
        return {
            "project_name": project_name,
            "director": director_name,
            "scene_number": scene_id,
            "include_metadata": include_metadata,
            "include_timestamps": include_timestamps,
        }
