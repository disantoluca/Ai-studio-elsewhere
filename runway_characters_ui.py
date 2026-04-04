#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎭 Runway Characters UI for AI Studio Elsewhere
Create and manage conversational AI avatars
"""

import streamlit as st
from runway_character_manager import get_character_manager
import logging

logger = logging.getLogger(__name__)

def display_character_creation_tab():
    """Display character creation interface with latest Runway features"""
    
    manager = get_character_manager()
    
    st.header("🎭 Create Film Characters (GWM-1)")
    st.write("Create conversational AI avatars powered by Runway's latest GWM-1 model")
    
    # Model selection
    st.subheader("🤖 Select Model")
    col1, col2 = st.columns(2)
    
    with col1:
        model = st.selectbox(
            "Video Model",
            list(manager.AVAILABLE_MODELS.keys()),
            help="Choose the generation model"
        )
        st.caption(manager.AVAILABLE_MODELS[model]["description"])
    
    with col2:
        voice_provider = st.selectbox(
            "Voice Provider",
            list(manager.VOICE_PROVIDERS.keys()),
            help="Choose voice synthesis provider"
        )
        st.caption(manager.VOICE_PROVIDERS[voice_provider])
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📸 Character Image")
        uploaded_file = st.file_uploader(
            "Upload character image (front-facing, high quality)",
            type=["jpg", "jpeg", "png"]
        )
        
        if uploaded_file:
            st.image(uploaded_file, caption="Character Reference", use_container_width=True)
            # In production, upload to S3 and get URL
            image_url = f"https://example.com/{uploaded_file.name}"
    
    with col2:
        st.subheader("⚙️ Character Settings")
        
        name = st.text_input("Character Name", placeholder="e.g., Director's Assistant")
        
        voice = st.selectbox(
            "Voice Style",
            manager.get_available_voices(),
            help="Choose how the character sounds"
        )
        
        voice_desc = manager.get_voice_samples().get(voice, "")
        st.caption(f"💬 {voice_desc}")
    
    st.markdown("---")
    
    st.subheader("📝 Character Personality")
    
    instructions = st.text_area(
        "System Instructions",
        placeholder="Describe the character's personality, role, and knowledge. E.g., 'You are a knowledgeable film production assistant who helps directors with cinematography, lighting, and scene planning.'",
        height=150
    )
    
    st.markdown("---")
    
    st.subheader("🎬 Starting Script (Optional)")
    
    starting_script = st.text_input(
        "Opening Line",
        placeholder="What should the character say when a conversation starts?",
        help="E.g., 'Hello! I'm your film production assistant. How can I help with your scene today?'"
    )
    
    st.markdown("---")
    
    # Create button
    if st.button("✨ Create Character", type="primary", use_container_width=True):
        if not name or not instructions:
            st.error("❌ Please fill in Character Name and System Instructions")
        elif not uploaded_file:
            st.error("❌ Please upload a character image")
        else:
            with st.spinner(f"🎬 Creating character with {model} and {voice_provider}..."):
                result = manager.create_character(
                    name=name,
                    image_url=image_url,
                    voice=voice,
                    voice_provider=voice_provider,
                    instructions=instructions,
                    starting_script=starting_script,
                    model=model
                )
                
                if "error" not in result:
                    st.success(f"✅ Character created: {name}")
                    st.balloons()
                    
                    # Display character info
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Character ID", result.get("id", "N/A")[:12])
                    with col2:
                        st.metric("Voice", voice)
                    with col3:
                        st.metric("Provider", voice_provider)
                    with col4:
                        st.metric("Status", "Active")
                else:
                    st.error(f"❌ Creation failed: {result['error']}")

def display_character_management():
    """Display character management interface"""
    
    manager = get_character_manager()
    
    st.header("🎭 Your Characters")
    st.write("View and manage all your film project characters")
    
    # Refresh button
    if st.button("🔄 Refresh Characters"):
        st.rerun()
    
    characters = manager.list_characters()
    
    if not characters:
        st.info("📭 No characters created yet. Create one in the 'Create Character' tab!")
        return
    
    # Display characters in grid
    cols = st.columns(2)
    
    for idx, character in enumerate(characters):
        with cols[idx % 2]:
            with st.container(border=True):
                st.subheader(f"🎭 {character.get('name', 'Unknown')}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("ID", character.get('id', 'N/A')[:12])
                with col2:
                    st.metric("Voice", character.get('voice', 'N/A'))
                
                # Character actions
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💬 Start Conversation", key=f"call_{character.get('id')}"):
                        start_character_call(character.get('id'))
                
                with col2:
                    if st.button("✏️ Edit", key=f"edit_{character.get('id')}"):
                        st.session_state.edit_character_id = character.get('id')
                        st.rerun()

def start_character_call(character_id: str):
    """Start a video call with a character"""
    
    manager = get_character_manager()
    
    st.info("💬 Starting conversation...")
    
    call_data = manager.start_video_call(character_id)
    
    if "error" not in call_data:
        st.success("✅ Call started!")
        st.session_state.active_call_id = call_data.get("callId")
        
        # Display video stream area
        st.markdown("---")
        st.write("**Video call area would appear here**")
        st.info("In a full implementation, this would show the real-time video feed")
        
        # Chat interface
        if "call_messages" not in st.session_state:
            st.session_state.call_messages = []
        
        # Display messages
        for message in st.session_state.call_messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        # Input
        user_message = st.chat_input("Type your message...")
        if user_message:
            st.session_state.call_messages.append({"role": "user", "content": user_message})
            st.session_state.call_messages.append(
                {"role": "assistant", "content": f"Character responds to: {user_message}"}
            )
            st.rerun()
    else:
        st.error(f"❌ Failed to start call: {call_data['error']}")

# Main UI
if __name__ == "__main__":
    st.set_page_config(page_title="Film Characters", layout="wide")
    
    tab1, tab2 = st.tabs(["Create Character", "Manage Characters"])
    
    with tab1:
        display_character_creation_tab()
    
    with tab2:
        display_character_management()
