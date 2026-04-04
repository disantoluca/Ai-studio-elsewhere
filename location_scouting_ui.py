#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌍 Google Places Location Scouting UI Component
For integration into AI Studio Elsewhere

Displays:
- Scene locations from your script
- Real-world reference locations
- Photos, ratings, details
- Buttons to generate concept images from locations
"""

import streamlit as st
import os
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

try:
    from google_places_agent import GooglePlacesAgent
    GOOGLE_PLACES_AVAILABLE = True
except ImportError:
    GOOGLE_PLACES_AVAILABLE = False
    logger.warning("⚠️ google_places_agent not available")

# ============================================================
# STREAMLIT UI COMPONENT
# ============================================================

def display_location_scouting():
    """Main location scouting interface for AI Studio"""
    
    st.header("🌍 Location Scouting & References")
    
    if not GOOGLE_PLACES_AVAILABLE:
        st.error("❌ Google Places Agent not loaded. Make sure google_places_agent.py is in the same directory.")
        return
    
    # Check for API key
    google_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    
    if not google_api_key:
        st.warning("⚠️ No Google Places API key configured")
        google_api_key = st.text_input("Enter Google Places API Key", type="password")
        os.environ["GOOGLE_PLACES_API_KEY"] = google_api_key
    
    if not google_api_key:
        st.info("Get a Google Places API key: https://console.cloud.google.com/")
        return
    
    # Create agent
    agent = GooglePlacesAgent(google_api_key)
    
    # Tabs
    tab_search, tab_scene_locations, tab_reference_map = st.tabs([
        "🔍 Search Locations",
        "🎬 Scene Locations",
        "📍 Reference Map"
    ])
    
    # ============================================================
    # TAB 1: SEARCH LOCATIONS
    # ============================================================
    
    with tab_search:
        st.subheader("🔍 Search for Locations")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_query = st.text_input(
                "Search for a location",
                placeholder="e.g., Shanghai rooftop, Yunnan village, Beijing cafe"
            )
        
        with col2:
            search_button = st.button("🔍 Search", type="primary", use_container_width=True)
        
        if search_button and search_query:
            with st.spinner("Searching..."):
                query, results = agent.extract_and_search(search_query)
                
                st.success(f"Found {len(results)} results for: {query}")
                
                # Display results
                for i, result in enumerate(results[:10]):  # Limit to 10
                    with st.expander(f"📍 {result['name']} ({i+1})"):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write(f"**Address:** {result['address']}")
                            if result['rating']:
                                st.write(f"**Rating:** ⭐ {result['rating']}")
                            if result['user_ratings_total']:
                                st.write(f"**Reviews:** {result['user_ratings_total']}")
                            
                            if result['location']:
                                st.write(f"**Coordinates:** {result['location']['lat']:.4f}, {result['location']['lng']:.4f}")
                        
                        with col2:
                            if result['opening_hours'] is not None:
                                status = "🟢 Open" if result['opening_hours'] else "🔴 Closed"
                                st.write(status)
                        
                        # Generate concept image button
                        if st.button(f"🎨 Generate Concept from Location", key=f"concept_{i}"):
                            st.session_state.selected_location = result
                            st.success(f"Selected: {result['name']}")
    
    # ============================================================
    # TAB 2: SCENE LOCATIONS
    # ============================================================
    
    with tab_scene_locations:
        st.subheader("🎬 Extract Locations from Your Scenes")
        
        st.write("Paste your scene description to auto-detect locations:")
        
        scene_text = st.text_area(
            "Scene description",
            placeholder="e.g., 他们在上海的老弄堂里行走，雾很浓。或 They walk through a foggy Shanghai alley at night.",
            height=150
        )
        
        if st.button("📍 Find Locations in Scene", type="primary", use_container_width=True):
            if scene_text:
                with st.spinner("Extracting locations..."):
                    query, results = agent.extract_and_search(scene_text)
                    
                    st.success(f"Detected location: **{query}**")
                    st.write(f"Found {len(results)} reference locations")
                    
                    # Display in columns
                    cols = st.columns(min(3, len(results)))
                    
                    for i, result in enumerate(results[:9]):
                        with cols[i % 3]:
                            st.write(f"### {result['name']}")
                            st.write(f"⭐ {result['rating'] or 'N/A'}")
                            st.write(f"📍 {result['address'][:50]}...")
                            
                            if st.button("Use as Reference", key=f"use_{i}"):
                                st.session_state.selected_location = result
                                st.success(f"Selected: {result['name']}")
            else:
                st.warning("Please enter a scene description")
    
    # ============================================================
    # TAB 3: REFERENCE MAP
    # ============================================================
    
    with tab_reference_map:
        st.subheader("📍 Location Reference Map")
        
        st.info("Select a location from 'Search Locations' or 'Scene Locations' to see it on the map")
        
        # Check if location is selected
        if "selected_location" in st.session_state:
            location = st.session_state.selected_location
            
            if location.get("location"):
                st.write(f"## {location['name']}")
                st.write(f"📍 {location['address']}")
                
                # Display map
                import pandas as pd
                map_data = pd.DataFrame({
                    'lat': [location['location']['lat']],
                    'lon': [location['location']['lng']]
                })
                st.map(map_data, zoom=16)
                
                # Display location details
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if location['rating']:
                        st.metric("Rating", f"{location['rating']}⭐")
                with col2:
                    if location['user_ratings_total']:
                        st.metric("Reviews", location['user_ratings_total'])
                with col3:
                    if location['opening_hours'] is not None:
                        status = "Open" if location['opening_hours'] else "Closed"
                        st.metric("Status", status)
                
                # Google Maps link
                lat = location['location']['lat']
                lng = location['location']['lng']
                maps_url = f"https://maps.google.com/?q={lat},{lng}"
                st.markdown(f"[🗺️ Open in Google Maps]({maps_url})")
                
                # Use for concept generation
                st.markdown("---")
                if st.button("🎨 Generate Concept Image from This Location", type="primary", use_container_width=True):
                    st.success(f"Ready to generate concept from: {location['name']}")
                    st.info("Go to 'Concept Images' tab with this location as reference")
        else:
            st.write("No location selected yet. Search for a location first!")

def display_location_selector_widget() -> Optional[Dict]:
    """
    Compact widget for sidebar - quick location selector
    Returns selected location or None
    """
    if not GOOGLE_PLACES_AVAILABLE:
        return None
    
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        return None
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🌍 Quick Location Search")
    
    location_query = st.sidebar.text_input(
        "Search location",
        placeholder="Shanghai rooftop"
    )
    
    if location_query:
        agent = GooglePlacesAgent(api_key)
        query, results = agent.extract_and_search(location_query)
        
        if results:
            location_names = [r['name'] for r in results[:5]]
            selected_name = st.sidebar.selectbox("Select location", location_names)
            
            # Find the selected result
            for result in results:
                if result['name'] == selected_name:
                    st.sidebar.write(f"**{result['name']}**")
                    st.sidebar.write(f"⭐ {result['rating'] or 'N/A'}")
                    return result
    
    return None

if __name__ == "__main__":
    # Standalone demo
    st.set_page_config(page_title="Location Scouting", layout="wide")
    display_location_scouting()
