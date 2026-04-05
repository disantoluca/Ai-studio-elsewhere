#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 Film Deck UI — Streamlit Integration
One-click professional pitch deck generation
"""

import streamlit as st
import os
from typing import List, Dict, Any, Optional


def display_film_deck_export(
    project,
    scenes: List[Dict[str, Any]] = None,
    storyboard: List[Dict[str, Any]] = None,
    storyboard_images: List[Optional[str]] = None,
    cover_image: Optional[str] = None
):
    """
    Display film deck export UI in Streamlit
    
    Args:
        project: Project object with title, director, etc.
        scenes: List of scene dicts
        storyboard: List of storyboard panel dicts
        storyboard_images: List of image paths
        cover_image: Optional cover image
    """
    
    st.markdown("---")
    st.subheader("🎬 Film Deck Export")
    st.caption("Professional pitch deck for directors, producers, and investors")
    
    # Deck settings
    col1, col2 = st.columns(2)
    
    with col1:
        title = st.text_input(
            "Deck Title",
            value=getattr(project, 'title_en', 'Untitled'),
            key="deck_title"
        )
    
    with col2:
        production_company = st.text_input(
            "Production Company",
            value="",
            key="production_company"
        )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        director = st.text_input(
            "Director",
            value=getattr(project, 'director', ''),
            key="deck_director"
        )
    
    with col2:
        year = st.number_input(
            "Year",
            value=2026,
            min_value=2020,
            max_value=2030,
            key="deck_year"
        )
    
    with col3:
        st.empty()  # Spacing
    
    # Content fields
    with st.expander("📝 Content"):
        
        logline = st.text_area(
            "Logline",
            value=getattr(project, 'logline', ''),
            height=60,
            key="deck_logline"
        )
        
        vision = st.text_area(
            "Director Vision",
            value="",
            height=120,
            placeholder="A poetic exploration of...",
            key="deck_vision"
        )
        
        # Tone selector
        tone_options = ["Cinematic", "Poetic", "Intimate", "Epic", "Surreal", "Documentary", "Experimental"]
        selected_tones = st.multiselect(
            "Mood & Tone",
            tone_options,
            default=["Cinematic"],
            key="deck_tone"
        )
    
    # Export button
    if st.button("📄 Generate Film Deck PDF", use_container_width=True):
        with st.spinner("🎬 Building film deck..."):
            try:
                from film_deck_generator import export_film_deck
                
                # Prepare scenes
                deck_scenes = []
                if scenes:
                    for scene in scenes:
                        deck_scenes.append({
                            "scene_number": scene.get('scene_number', ''),
                            "heading": scene.get('heading', ''),
                            "location": scene.get('location', ''),
                            "action": scene.get('action', ''),
                            "description": scene.get('action', ''),
                        })
                
                # Validate storyboard images
                valid_images = []
                if storyboard_images:
                    for img_path in storyboard_images:
                        if img_path and os.path.exists(img_path):
                            valid_images.append(img_path)
                        else:
                            valid_images.append(None)
                
                # Generate deck
                pdf_path = export_film_deck(
                    title=title,
                    director=director,
                    logline=logline,
                    vision=vision,
                    tone=selected_tones,
                    scenes=deck_scenes,
                    storyboard=storyboard,
                    storyboard_images=valid_images,
                    cover_image=cover_image,
                    production_company=production_company,
                    year=int(year),
                    output_dir="exports"
                )
                
                if pdf_path and os.path.exists(pdf_path):
                    
                    # Read PDF
                    with open(pdf_path, "rb") as pdf_file:
                        pdf_data = pdf_file.read()
                    
                    # Download button
                    st.download_button(
                        label="📥 Download Film Deck",
                        data=pdf_data,
                        file_name=os.path.basename(pdf_path),
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    st.success(f"✅ Film deck ready: {os.path.basename(pdf_path)}")
                    st.caption(f"📊 Pages: ~{3 + len(deck_scenes) + (len(storyboard) if storyboard else 0)} | Size: {len(pdf_data)/1024:.1f} KB")
                
                else:
                    st.error("❌ PDF generation failed")
            
            except ImportError:
                st.error("❌ film_deck_generator module not found")
            except Exception as e:
                st.error(f"❌ Error: {str(e)[:100]}")


def display_deck_preview(
    title: str,
    director: str,
    logline: str,
    tone: List[str]
):
    """Display preview of deck content"""
    
    with st.expander("👁️ Deck Preview", expanded=False):
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Title**")
            st.caption(title or "Untitled")
            
            st.write("**Director**")
            st.caption(director or "N/A")
        
        with col2:
            st.write("**Logline**")
            st.caption(logline[:100] + "..." if logline else "N/A")
            
            st.write("**Tone**")
            st.caption(" • ".join(tone) if tone else "N/A")
