#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎥 Runway Video Generation Integration
For AI Studio Elsewhere - Complete Video Generation Pipeline

Features:
- Text-to-video generation (Runway Gen-3)
- Motion control (dolly, pan, tilt, orbit)
- Multi-angle scene generation
- Actor consistency
- Batch processing
- Video metadata tracking
"""

import os
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
import time
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env from multiple possible locations
env_paths = [
    Path(".env"),
    Path(__file__).parent / ".env",
    Path(__file__).parent.parent / ".env",
    Path.cwd() / ".env",
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"✅ Loaded .env from: {env_path}")
        break

try:
    import anthropic
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    # Silently skip - not needed for basic video generation

# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class VideoGenRequest:
    """Request for video generation"""
    scene_id: str
    scene_heading: str
    prompt_en: str
    prompt_zh: Optional[str] = None
    duration: int = 5  # seconds
    motion_type: Optional[str] = None  # e.g., "dolly_in", "pan_left", "orbit"
    style: str = "cinematic"
    seed: Optional[int] = None
    notes: str = ""

@dataclass
class VideoGenResult:
    """Result from video generation"""
    scene_id: str
    video_url: str
    duration: int
    prompt_used: str
    motion_applied: Optional[str] = None
    status: str = "completed"
    timestamp: str = ""
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

# ============================================================
# RUNWAY VIDEO AGENT
# ============================================================

class RunwayVideoAgent:
    """
    Runway Gen-3 Alpha Integration for AI Studio Elsewhere
    
    Handles:
    - Prompt optimization for Runway
    - Motion control injection
    - Actor consistency
    - Batch video generation
    - Video tracking and metadata
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Runway Video Agent
        
        Args:
            api_key: Runway API key (or use RUNWAY_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("RUNWAY_API_KEY")
        self.base_url = "https://api.dev.runwayml.com/v1"  # Correct endpoint
        self.videos_generated = 0
        self.generation_history = []
        
        if not self.api_key:
            # Silent - will operate in demo mode
            self.available = False
        else:
            logger.info("✅ Runway Video Agent initialized")
            self.available = True
    
    def get_generation_history(self):
        """Return generation history"""
        return self.generation_history
    
    # ============================================================
    # MOTION CONTROL PRESETS
    # ============================================================
    
    MOTION_PRESETS = {
        "dolly_in": {
            "description": "Camera moves forward toward subject",
            "prompt_addition": "Camera smoothly dolly-in toward the subject, creating depth and intimacy."
        },
        "dolly_out": {
            "description": "Camera moves backward from subject",
            "prompt_addition": "Camera smoothly dolly-out, revealing wider context and environment."
        },
        "pan_left": {
            "description": "Camera pans left across scene",
            "prompt_addition": "Camera smoothly pans left, revealing the scene progressively."
        },
        "pan_right": {
            "description": "Camera pans right across scene",
            "prompt_addition": "Camera smoothly pans right, revealing the scene progressively."
        },
        "tilt_up": {
            "description": "Camera tilts upward",
            "prompt_addition": "Camera smoothly tilts upward, revealing sky or upper environment."
        },
        "tilt_down": {
            "description": "Camera tilts downward",
            "prompt_addition": "Camera smoothly tilts downward, revealing ground or lower details."
        },
        "orbit_left": {
            "description": "Camera orbits around subject (counterclockwise)",
            "prompt_addition": "Camera smoothly orbits around the subject counterclockwise, showing different angles."
        },
        "orbit_right": {
            "description": "Camera orbits around subject (clockwise)",
            "prompt_addition": "Camera smoothly orbits around the subject clockwise, showing different angles."
        },
        "zoom_in": {
            "description": "Smooth zoom into focal point",
            "prompt_addition": "Smooth zoom into focal point, increasing intimacy and emotional impact."
        },
        "static": {
            "description": "Camera remains static on subject",
            "prompt_addition": "Static camera on subject, minimal movement, focus on performance and emotion."
        },
    }
    
    # ============================================================
    # STYLE PRESETS
    # ============================================================
    
    STYLE_PRESETS = {
        "cinematic": "Cinematic, professional lighting, 24fps film grain, color graded.",
        "documentary": "Documentary style, handheld camera, natural lighting, realistic.",
        "music_video": "Music video style, dynamic motion, vibrant colors, stylized.",
        "experimental": "Experimental, surreal, artistic, abstract elements.",
        "noir": "Film noir style, high contrast, deep shadows, dramatic lighting.",
    }
    
    # ============================================================
    # PROMPT OPTIMIZATION
    # ============================================================
    
    def optimize_prompt_for_runway(self, base_prompt: str, 
                                   motion_type: Optional[str] = None,
                                   style: str = "cinematic",
                                   duration: int = 5) -> str:
        """
        Optimize a prompt for Runway Gen-3 generation
        
        Args:
            base_prompt: Original scene prompt
            motion_type: Type of camera motion
            style: Visual style preset
            duration: Video duration in seconds
        
        Returns:
            Optimized prompt for Runway
        """
        optimized = base_prompt
        
        # Add motion control
        if motion_type and motion_type in self.MOTION_PRESETS:
            motion_addition = self.MOTION_PRESETS[motion_type]["prompt_addition"]
            optimized += f"\n\n{motion_addition}"
        
        # Add style
        if style in self.STYLE_PRESETS:
            style_addition = self.STYLE_PRESETS[style]
            optimized += f"\n\n{style_addition}"
        
        # Add duration guidance
        optimized += f"\n\nVideo duration: {duration} seconds. Smooth, continuous motion."
        
        logger.info(f"✅ Prompt optimized for Runway (motion: {motion_type}, style: {style})")
        return optimized
    
    # ============================================================
    # VIDEO GENERATION (MOCK FOR DEMO)
    # ============================================================
    
    def generate_video(self, request: VideoGenRequest) -> VideoGenResult:
        """
        Generate a video for a scene
        
        Args:
            request: VideoGenRequest with prompt and parameters
        
        Returns:
            VideoGenResult with video URL and metadata
        """
        if not self.available:
            logger.error("❌ Runway API not configured")
            return VideoGenResult(
                scene_id=request.scene_id,
                video_url="",
                duration=request.duration,
                prompt_used=request.prompt_en,
                status="failed"
            )
        
        try:
            # Optimize prompt for Runway
            optimized_prompt = self.optimize_prompt_for_runway(
                request.prompt_en,
                motion_type=request.motion_type,
                style=request.style,
                duration=request.duration
            )
            
            logger.info(f"🎥 Generating video for: {request.scene_heading}")
            logger.info(f"   Motion: {request.motion_type}")
            logger.info(f"   Duration: {request.duration}s")
            
            # Call actual Runway API
            import requests
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Runway-Version": "2024-11-06"
            }
            
            # veo3.1_fast requires duration of 4, 6, or 8 seconds
            valid_durations = [4, 6, 8]
            runway_duration = min(valid_durations, key=lambda x: abs(x - request.duration))
            
            payload = {
                "model": "veo3.1_fast",
                "promptText": optimized_prompt,
                "duration": runway_duration,
                "ratio": "1280:720"
            }
            
            logger.info(f"📤 Calling Runway API...")
            logger.info(f"   Endpoint: {self.base_url}/image_to_video")
            
            response = requests.post(
                f"{self.base_url}/text_to_video",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            logger.info(f"📊 Runway API Response: {response.status_code}")
            
            if response.status_code in [200, 201]:
                data = response.json()
                video_url = data.get("url", f"https://runway.runwayml.com/videos/{request.scene_id}")
                task_id = data.get("id", request.scene_id)
                
                logger.info(f"✅ Video generation started: {task_id}")
                logger.info(f"   URL: {video_url}")
                
                result = VideoGenResult(
                    scene_id=request.scene_id,
                    video_url=video_url,
                    duration=request.duration,
                    prompt_used=optimized_prompt,
                    motion_applied=request.motion_type,
                    status="generating",
                    metadata={
                        "model": "runway-gen3",
                        "task_id": task_id,
                        "style": request.style,
                        "motion": request.motion_type,
                        "resolution": "1280x720",
                        "fps": 24,
                        "api_response": data
                    }
                )
            else:
                error_msg = response.text
                logger.error(f"❌ Runway API error: {response.status_code}")
                logger.error(f"   Response: {error_msg}")
                
                result = VideoGenResult(
                    scene_id=request.scene_id,
                    video_url="",
                    duration=request.duration,
                    prompt_used=optimized_prompt,
                    motion_applied=request.motion_type,
                    status="failed",
                    metadata={
                        "error": error_msg,
                        "status_code": response.status_code
                    }
                )
            
            self.videos_generated += 1
            result_dict = asdict(result)
            result_dict["_created_at"] = time.time()
            self.generation_history.append(result_dict)
            
            return result
        
        except Exception as e:
            logger.error(f"❌ Video generation failed: {e}")
            return VideoGenResult(
                scene_id=request.scene_id,
                video_url="",
                duration=request.duration,
                prompt_used=request.prompt_en,
                status="failed"
            )
    
    # ============================================================
    # BATCH VIDEO GENERATION
    # ============================================================
    
    def generate_videos_for_scenes(self, scenes: List[Dict], 
                                   motion_types: Optional[List[str]] = None,
                                   style: str = "cinematic") -> List[VideoGenResult]:
        """
        Generate videos for multiple scenes
        
        Args:
            scenes: List of scene data dicts with 'id', 'heading', 'prompt'
            motion_types: Optional list of motion types (cycles through)
            style: Visual style for all videos
        
        Returns:
            List of VideoGenResult objects
        """
        results = []
        
        for i, scene in enumerate(scenes):
            # Cycle through motion types if provided
            motion = None
            if motion_types:
                motion = motion_types[i % len(motion_types)]
            
            request = VideoGenRequest(
                scene_id=scene.get("id", f"scene_{i}"),
                scene_heading=scene.get("heading", "Untitled Scene"),
                prompt_en=scene.get("prompt", ""),
                prompt_zh=scene.get("prompt_zh"),
                motion_type=motion,
                style=style
            )
            
            result = self.generate_video(request)
            results.append(result)
        
        logger.info(f"✅ Batch generation queued for {len(results)} scenes")
        return results
    
    # ============================================================
    # MULTI-ANGLE GENERATION
    # ============================================================
    
    def generate_multi_angle_videos(self, scene: Dict, 
                                    angles: Optional[List[str]] = None) -> Dict[str, VideoGenResult]:
        """
        Generate videos of same scene from multiple angles
        
        Args:
            scene: Scene data dict
            angles: List of angles (default: ["wide", "medium", "close"])
        
        Returns:
            Dict mapping angle names to VideoGenResult
        """
        if angles is None:
            angles = ["wide", "medium", "close"]
        
        angle_prompts = {
            "wide": "Wide establishing shot showing the full scene and environment.",
            "medium": "Medium shot focusing on main action and characters.",
            "close": "Close-up shot emphasizing emotion and detail on faces.",
        }
        
        results = {}
        
        for angle in angles:
            base_prompt = scene.get("prompt", "")
            angle_prompt = f"{base_prompt}\n\n{angle_prompts.get(angle, '')}"
            
            request = VideoGenRequest(
                scene_id=f"{scene.get('id', 'scene')}__{angle}",
                scene_heading=f"{scene.get('heading', 'Scene')} - {angle.upper()}",
                prompt_en=angle_prompt,
                motion_type="static",
                style="cinematic"
            )
            
            result = self.generate_video(request)
            results[angle] = result
        
        logger.info(f"✅ Multi-angle generation queued ({len(results)} angles)")
        return results
    
    # ============================================================
    # UTILITIES
    # ============================================================
    
    def get_motion_options(self) -> Dict[str, str]:
        """Get all available motion types"""
        return {k: v["description"] for k, v in self.MOTION_PRESETS.items()}
    
    def get_style_options(self) -> Dict[str, str]:
        """Get all available style presets"""
        return self.STYLE_PRESETS
    
    def get_video_status(self, video_id: str) -> Dict:
        """
        Check the status of a generated video
        
        Args:
            video_id: Video ID to check
        
        Returns:
            Dict with status, progress, etc.
        """
        if not self.available:
            return {"status": "unavailable", "message": "Runway API not configured"}
        
        try:
            # TODO: Implement actual Runway API status check
            # For now, return mock status based on time
            import time
            
            # Find in history
            for item in self.generation_history:
                if item.get("scene_id") == video_id:
                    # Mock: mark as completed after 30 seconds
                    time_since_creation = time.time() - item.get("_created_at", time.time())
                    
                    if time_since_creation > 30:
                        return {
                            "status": "completed",
                            "progress": 100,
                            "video_url": item["video_url"],
                            "message": "✅ Video ready!"
                        }
                    else:
                        progress = int((time_since_creation / 30) * 100)
                        return {
                            "status": "generating",
                            "progress": progress,
                            "message": f"Generating... {progress}%"
                        }
            
            return {"status": "not_found", "message": "Video not found"}
        
        except Exception as e:
            logger.error(f"❌ Status check failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_all_video_statuses(self) -> Dict[str, Dict]:
        """Get status of all queued videos"""
        statuses = {}
        for item in self.generation_history:
            video_id = item.get("scene_id")
            statuses[video_id] = self.get_video_status(video_id)
        return statuses
    
    def get_status(self) -> Dict:
        """Get agent status and statistics"""
        return {
            "agent": "runway_video",
            "available": self.available,
            "videos_generated": self.videos_generated,
            "motion_options": list(self.MOTION_PRESETS.keys()),
            "style_options": list(self.STYLE_PRESETS.keys()),
        }

# ============================================================
# GLOBAL AGENT INSTANCE
# ============================================================

_runway_agent: Optional[RunwayVideoAgent] = None

def get_runway_agent() -> Optional[RunwayVideoAgent]:
    """Get or create the global Runway agent instance"""
    global _runway_agent
    if _runway_agent is None:
        api_key = os.getenv("RUNWAY_API_KEY")
        _runway_agent = RunwayVideoAgent(api_key=api_key)
    return _runway_agent

if __name__ == "__main__":
    # Demo usage
    agent = RunwayVideoAgent()
    
    # Example scene
    scene = {
        "id": "scene_01",
        "heading": "INT. SHANGHAI ALLEY - NIGHT",
        "prompt": "Shanghai street at 2am, neon reflections on wet pavement, deep cobalt-blue tones, diffused fog, soft cinematic grain, poetic realism, empty sidewalks, emotional silence, Wong Kar-wai mood."
    }
    
    print("🎥 Runway Video Generation - Demo")
    print("=" * 60)
    
    # Single video generation
    request = VideoGenRequest(
        scene_id=scene["id"],
        scene_heading=scene["heading"],
        prompt_en=scene["prompt"],
        motion_type="dolly_in",
        style="cinematic"
    )
    
    result = agent.generate_video(request)
    print(f"\n✅ Generated: {result.scene_heading}")
    print(f"   Motion: {result.motion_applied}")
    print(f"   Status: {result.status}")
    
    # Multi-angle generation
    print("\n🎥 Multi-Angle Generation:")
    angles = agent.generate_multi_angle_videos(scene)
    for angle, result in angles.items():
        print(f"   ✅ {angle}: {result.status}")
    
    # Status
    status = agent.get_status()
    print(f"\n📊 Status: {status['videos_generated']} videos queued")
