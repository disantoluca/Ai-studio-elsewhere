#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 Scene 1 Video Status Dashboard
Real-time tracking of video generation progress
"""

import streamlit as st
import sys
from pathlib import Path
import time
from typing import Dict

# Add agents folder to path
sys.path.insert(0, str(Path.cwd() / "agents"))
sys.path.insert(0, str(Path(__file__).parent / "agents"))

try:
    from runway_video_agent import get_runway_agent
except ImportError:
    # Try from agents subfolder
    from agents.runway_video_agent import get_runway_agent

def display_video_status_dashboard():
    """Show real-time status of all queued videos"""
    
    st.header("📹 Video Generation Status")
    
    agent = get_runway_agent()
    
    if not agent.generation_history:
        st.info("No videos generated yet. Go to Scene 1 Video UI to queue videos!")
        return
    
    # Auto-refresh every 5 seconds
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    # Get all statuses
    statuses = agent.get_all_video_statuses()
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    completed = sum(1 for s in statuses.values() if s.get("status") == "completed")
    generating = sum(1 for s in statuses.values() if s.get("status") == "generating")
    failed = sum(1 for s in statuses.values() if s.get("status") == "failed")
    
    with col1:
        st.metric("Completed", completed, f"/{len(statuses)}")
    with col2:
        st.metric("Generating", generating)
    with col3:
        st.metric("Failed", failed)
    with col4:
        overall_progress = int((completed / len(statuses)) * 100) if statuses else 0
        st.metric("Overall", f"{overall_progress}%")
    
    st.markdown("---")
    
    # Detailed status for each video
    st.subheader("📊 Detailed Status")
    
    # Organize by status
    tabs = st.tabs(["All", "✅ Completed", "⏳ Generating", "❌ Failed"])
    
    with tabs[0]:  # All
        for video_id, status in statuses.items():
            display_video_status_card(video_id, status)
    
    with tabs[1]:  # Completed
        for video_id, status in statuses.items():
            if status.get("status") == "completed":
                display_video_status_card(video_id, status)
    
    with tabs[2]:  # Generating
        for video_id, status in statuses.items():
            if status.get("status") == "generating":
                display_video_status_card(video_id, status)
    
    with tabs[3]:  # Failed
        for video_id, status in statuses.items():
            if status.get("status") == "failed":
                display_video_status_card(video_id, status)
    
    # Auto-refresh indicator
    st.markdown("---")
    st.info("💡 This page auto-refreshes. Press 🔄 Refresh to check immediately, or reload the page.")
    
    # Set auto-rerun timer if any are generating
    if generating > 0:
        time.sleep(5)
        st.rerun()

def display_video_status_card(video_id: str, status: Dict):
    """Display a single video status card"""
    
    status_text = status.get("status", "unknown")
    message = status.get("message", "")
    progress = status.get("progress", 0)
    
    # Color code by status
    if status_text == "completed":
        color = "🟢"
        emoji = "✅"
    elif status_text == "generating":
        color = "🟡"
        emoji = "⏳"
    else:
        color = "🔴"
        emoji = "❌"
    
    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.write(f"**{video_id}**")
            st.caption(message)
        
        with col2:
            st.write(f"{emoji} {status_text.upper()}")
        
        with col3:
            if status_text == "generating":
                st.progress(progress / 100)
        
        # Show video URL if completed
        if status_text == "completed" and status.get("video_url"):
            st.markdown(f"[📹 Watch Video]({status['video_url']})")

if __name__ == "__main__":
    st.set_page_config(page_title="Video Status", layout="wide")
    display_video_status_dashboard()
