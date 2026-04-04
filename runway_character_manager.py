#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎭 Runway Characters API Integration
Create and manage conversational AI avatars for film projects

Features:
- Create characters from images
- Configure voice, personality, knowledge
- Real-time video conversations
- Custom instructions & starting scripts
"""

import os
import json
import logging
from typing import Dict, Optional, List
import requests

logger = logging.getLogger(__name__)

# ============================================================
# CHARACTER MANAGER
# ============================================================

class RunwayCharacterManager:
    """Manage Runway Characters API interactions"""
    
    # Latest available models
    AVAILABLE_MODELS = {
        "gwm-avatars": {
            "name": "GWM-1 Avatars",
            "description": "Real-time interactive avatars (latest)",
            "type": "realtime"
        },
        "Gen-4.5": {
            "name": "Gen-4.5",
            "description": "State-of-the-art text/image to video",
            "type": "video"
        },
        "Gen-4-Turbo": {
            "name": "Gen-4 Turbo",
            "description": "Fastest image to video",
            "type": "video"
        },
        "Gen-4-Aleph": {
            "name": "Gen-4 Aleph",
            "description": "Video editing and transformation",
            "type": "video"
        },
        "Act-Two": {
            "name": "Act Two",
            "description": "Next-gen motion capture",
            "type": "video"
        },
    }
    
    VOICE_PROVIDERS = {
        "elevenlabs": "ElevenLabs (29 languages, premium quality)",
        "runway": "Runway Native (integrated, fast)"
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize character manager with latest Runway API
        
        Args:
            api_key: Runway API key
        """
        self.api_key = api_key or os.getenv("RUNWAY_API_KEY")
        self.base_url = "https://api.dev.runwayml.com/v1"
        self.available = bool(self.api_key)
        
        if self.available:
            logger.info("✅ Runway Characters API (GWM-1) initialized")
        else:
            logger.warning("⚠️ Runway API key not configured")
    
    # ============================================================
    # CHARACTER CREATION
    # ============================================================
    
    def create_character(
        self,
        name: str,
        image_url: str,
        voice: str = "professional",
        voice_provider: str = "runway",
        instructions: str = "",
        starting_script: str = "",
        model: str = "gwm-avatars"  # Latest model by default
    ) -> Dict:
        """
        Create a new Runway character with GWM-1
        
        Args:
            name: Character name
            image_url: URL to character image (front-facing, high quality)
            voice: Voice preset (professional, casual, warm, etc.)
            voice_provider: "runway" or "elevenlabs" (supports 29 languages)
            instructions: Character system instructions/personality
            starting_script: Opening line for conversations
            model: Model to use (gwm-avatars is latest)
        
        Returns:
            Character data with ID and configuration
        """
        if not self.available:
            logger.error("❌ Runway API not configured")
            return {"error": "API not configured"}
        
        try:
            payload = {
                "model": model,  # Use GWM-1 avatars
                "name": name,
                "imageUrl": image_url,
                "voice": {
                    "preset": voice,
                    "provider": voice_provider
                },
                "instructions": instructions,
                "startingScript": starting_script,
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Runway-Version": "2024-11-06"
            }
            
            response = requests.post(
                f"{self.base_url}/characters/create",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                character = response.json()
                logger.info(f"✅ Character created: {name} (Model: {model}, Voice: {voice_provider})")
                return character
            else:
                error = response.json().get("error", f"Status {response.status_code}")
                logger.error(f"❌ Character creation failed: {error}")
                return {"error": error}
        
        except Exception as e:
            logger.error(f"❌ Character creation error: {e}")
            return {"error": str(e)}
    
    # ============================================================
    # CHARACTER RETRIEVAL
    # ============================================================
    
    def list_characters(self) -> List[Dict]:
        """List all characters in your account"""
        if not self.available:
            return []
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-Runway-Version": "2024-11-06"
            }
            
            response = requests.get(
                f"{self.base_url}/characters",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                characters = response.json().get("characters", [])
                logger.info(f"✅ Retrieved {len(characters)} characters")
                return characters
            else:
                logger.error(f"❌ Failed to list characters: {response.status_code}")
                return []
        
        except Exception as e:
            logger.error(f"❌ Character list error: {e}")
            return []
    
    def get_character(self, character_id: str) -> Dict:
        """Get details for a specific character"""
        if not self.available:
            return {}
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-Runway-Version": "2024-11-06"
            }
            
            response = requests.get(
                f"{self.base_url}/characters/{character_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ Failed to get character: {response.status_code}")
                return {}
        
        except Exception as e:
            logger.error(f"❌ Get character error: {e}")
            return {}
    
    # ============================================================
    # CHARACTER UPDATES
    # ============================================================
    
    def update_character(
        self,
        character_id: str,
        name: Optional[str] = None,
        voice: Optional[str] = None,
        instructions: Optional[str] = None,
        starting_script: Optional[str] = None
    ) -> Dict:
        """Update character properties"""
        if not self.available:
            return {"error": "API not configured"}
        
        try:
            payload = {}
            if name:
                payload["name"] = name
            if voice:
                payload["voice"] = voice
            if instructions:
                payload["instructions"] = instructions
            if starting_script:
                payload["startingScript"] = starting_script
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Runway-Version": "2024-11-06"
            }
            
            response = requests.patch(
                f"{self.base_url}/characters/{character_id}",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Character updated: {character_id}")
                return response.json()
            else:
                error = response.json().get("error", f"Status {response.status_code}")
                logger.error(f"❌ Update failed: {error}")
                return {"error": error}
        
        except Exception as e:
            logger.error(f"❌ Update error: {e}")
            return {"error": str(e)}
    
    # ============================================================
    # VIDEO CALLS
    # ============================================================
    
    def start_video_call(self, character_id: str, message: str = "") -> Dict:
        """
        Start a video call with a character
        
        Args:
            character_id: Character to call
            message: Initial message to send
        
        Returns:
            Call session data with video stream
        """
        if not self.available:
            return {"error": "API not configured"}
        
        try:
            payload = {
                "characterId": character_id,
                "initialMessage": message
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Runway-Version": "2024-11-06"
            }
            
            response = requests.post(
                f"{self.base_url}/characters/call",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                call_data = response.json()
                logger.info(f"✅ Video call started: {call_data.get('callId')}")
                return call_data
            else:
                error = response.json().get("error", f"Status {response.status_code}")
                logger.error(f"❌ Call failed: {error}")
                return {"error": error}
        
        except Exception as e:
            logger.error(f"❌ Call error: {e}")
            return {"error": str(e)}
    
    def end_video_call(self, call_id: str) -> bool:
        """End an active video call"""
        if not self.available:
            return False
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-Runway-Version": "2024-11-06"
            }
            
            response = requests.post(
                f"{self.base_url}/characters/call/{call_id}/end",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Call ended: {call_id}")
                return True
            else:
                logger.error(f"❌ Failed to end call: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"❌ End call error: {e}")
            return False
    
    # ============================================================
    # PRESETS
    # ============================================================
    
    def get_available_voices(self) -> List[str]:
        """Get list of available voice presets"""
        return [
            "professional",
            "casual",
            "warm",
            "energetic",
            "calm",
            "friendly",
            "authoritative",
            "sarcastic",
        ]
    
    def get_voice_samples(self) -> Dict[str, str]:
        """Get sample audio for each voice"""
        return {
            "professional": "A formal, business-appropriate tone",
            "casual": "Relaxed, conversational style",
            "warm": "Friendly and welcoming",
            "energetic": "Enthusiastic and upbeat",
            "calm": "Serene and peaceful",
            "friendly": "Approachable and personable",
            "authoritative": "Confident and commanding",
            "sarcastic": "Witty and playful",
        }

# ============================================================
# GLOBAL INSTANCE
# ============================================================

_character_manager: Optional[RunwayCharacterManager] = None

def get_character_manager() -> RunwayCharacterManager:
    """Get or create global character manager"""
    global _character_manager
    if _character_manager is None:
        _character_manager = RunwayCharacterManager()
    return _character_manager

if __name__ == "__main__":
    # Demo
    manager = RunwayCharacterManager()
    
    print("🎭 Runway Characters API")
    print("=" * 60)
    print("\nAvailable voices:")
    for voice in manager.get_available_voices():
        print(f"  - {voice}")
    
    print("\nExample character creation:")
    print("""
    character = manager.create_character(
        name="Director Assistant",
        image_url="https://example.com/director.jpg",
        voice="professional",
        instructions="You are a helpful film production assistant...",
        starting_script="Hello! How can I help with your film today?"
    )
    """)
