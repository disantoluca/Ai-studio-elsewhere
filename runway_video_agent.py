#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎥 Runway Video Generation Integration
For AI Studio Elsewhere - Complete Video Generation Pipeline

Uses the official runwayml Python SDK.
Supports Gen-4.5 (text-to-video and image-to-video).

Features:
- Text-to-video generation (Runway Gen-4.5 / Gen-4 Turbo)
- Motion control via prompt engineering
- Multi-angle scene generation
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
]
for p in env_paths:
    if p.exists():
        load_dotenv(p, override=True)
        break

# Try importing the official SDK
try:
    from runwayml import RunwayML, TaskFailedError
    RUNWAY_SDK_AVAILABLE = True
except ImportError:
    RUNWAY_SDK_AVAILABLE = False
    logger.warning("⚠️ runwayml SDK not installed. pip install runwayml")

# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class VideoGenRequest:
    """Request for video generation"""
    scene_id: str
    scene_heading: str
    prompt_en: str
    prompt_zh: Optional[str] = None
    duration: int = 5  # seconds (2-10 supported)
    motion_type: Optional[str] = None
    style: str = "cinematic"
    seed: Optional[int] = None
    notes: str = ""
    prompt_image: Optional[str] = None  # URL or base64 data URI for image-to-video

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
    Runway Video Generation Agent using official SDK
    
    Handles:
    - Prompt optimization for Runway
    - Motion control injection
    - Text-to-video and image-to-video
    - Batch video generation
    - Video tracking and metadata
    """
    
    # Default model - gen4_turbo is cheaper, gen4.5 is higher quality
    DEFAULT_MODEL = "gen4_turbo"
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Runway Video Agent
        
        Args:
            api_key: Runway API secret. Reads from RUNWAYML_API_SECRET or RUNWAY_API_KEY env var.
            model: Model to use (gen4.5, gen4_turbo, veo3.1_fast, etc.)
        """
        # The SDK reads RUNWAYML_API_SECRET by default
        # But we also support RUNWAY_API_KEY for backwards compatibility
        self.api_key = api_key or os.getenv("RUNWAYML_API_SECRET") or os.getenv("RUNWAY_API_KEY")
        self.model = model or os.getenv("RUNWAY_MODEL", self.DEFAULT_MODEL)
        self.videos_generated = 0
        self.generation_history = []
        self.client = None
        
        if not RUNWAY_SDK_AVAILABLE:
            logger.error("❌ runwayml SDK not installed")
            self.available = False
        elif not self.api_key:
            logger.warning("⚠️ No Runway API key found")
            self.available = False
        else:
            try:
                # Set env var so SDK picks it up
                os.environ["RUNWAYML_API_SECRET"] = self.api_key
                self.client = RunwayML()
                logger.info(f"✅ Runway Video Agent initialized (model: {self.model})")
                self.available = True
            except Exception as e:
                logger.error(f"❌ Failed to initialize Runway client: {e}")
                self.available = False
    
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
        """Optimize a prompt for Runway generation"""
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
        
        logger.info(f"✅ Prompt optimized (motion: {motion_type}, style: {style})")
        return optimized
    
    # ============================================================
    # VIDEO GENERATION
    # ============================================================
    
    def generate_video(self, request: VideoGenRequest) -> VideoGenResult:
        """
        Generate a video using the Runway SDK.
        
        Supports both text-to-video (no image) and image-to-video.
        Uses .wait_for_task_output() for automatic polling.
        """
        if not self.available or not self.client:
            logger.error("❌ Runway API not configured")
            return VideoGenResult(
                scene_id=request.scene_id,
                video_url="",
                duration=request.duration,
                prompt_used=request.prompt_en,
                status="failed",
                metadata={"error": "Runway API not configured"}
            )
        
        try:
            # Optimize prompt
            optimized_prompt = self.optimize_prompt_for_runway(
                request.prompt_en,
                motion_type=request.motion_type,
                style=request.style,
                duration=request.duration
            )
            
            logger.info(f"🎥 Generating video for: {request.scene_heading}")
            logger.info(f"   Model: {self.model}")
            logger.info(f"   Motion: {request.motion_type}")
            logger.info(f"   Duration: {request.duration}s")
            
            # Clamp duration to valid range (2-10 seconds)
            duration = max(2, min(10, request.duration))
            
            # Build kwargs for the SDK call
            create_kwargs = {
                "model": self.model,
                "prompt_text": optimized_prompt,
                "ratio": "1280:720",
                "duration": duration,
            }
            
            # Add image if provided (image-to-video mode)
            if request.prompt_image:
                create_kwargs["prompt_image"] = request.prompt_image
            
            # Call the Runway SDK
            # image_to_video handles both text-to-video (omit prompt_image) and image-to-video
            task = self.client.image_to_video.create(
                **create_kwargs
            ).wait_for_task_output()
            
            # Extract video URL from task output
            video_url = ""
            if task and hasattr(task, 'output') and task.output:
                if isinstance(task.output, list) and len(task.output) > 0:
                    video_url = task.output[0]
                elif isinstance(task.output, str):
                    video_url = task.output
            
            logger.info(f"✅ Video generated: {video_url[:80] if video_url else 'no URL'}...")
            
            result = VideoGenResult(
                scene_id=request.scene_id,
                video_url=video_url,
                duration=duration,
                prompt_used=optimized_prompt,
                motion_applied=request.motion_type,
                status="completed",
                metadata={
                    "model": self.model,
                    "style": request.style,
                    "motion": request.motion_type,
                    "resolution": "1280x720",
                }
            )
            
        except Exception as e:
            error_name = type(e).__name__
            logger.error(f"❌ Video generation failed ({error_name}): {e}")
            result = VideoGenResult(
                scene_id=request.scene_id,
                video_url="",
                duration=request.duration,
                prompt_used=request.prompt_en,
                motion_applied=request.motion_type,
                status="failed",
                metadata={"error": f"{error_name}: {str(e)}"}
            )
        
        self.videos_generated += 1
        result_dict = asdict(result)
        result_dict["_created_at"] = time.time()
        self.generation_history.append(result_dict)
        
        return result
    
    # ============================================================
    # BATCH VIDEO GENERATION
    # ============================================================
    
    def generate_videos_for_scenes(self, scenes: List[Dict], 
                                   motion_types: Optional[List[str]] = None,
                                   style: str = "cinematic") -> List[VideoGenResult]:
        """Generate videos for multiple scenes"""
        results = []
        
        for i, scene in enumerate(scenes):
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
        
        logger.info(f"✅ Batch generation complete: {len(results)} scenes")
        return results
    
    # ============================================================
    # MULTI-ANGLE GENERATION
    # ============================================================
    
    def generate_multi_angle_videos(self, scene: Dict, 
                                    angles: Optional[List[str]] = None) -> Dict[str, VideoGenResult]:
        """Generate videos of same scene from multiple angles"""
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
        
        logger.info(f"✅ Multi-angle generation complete ({len(results)} angles)")
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
        """Check the status of a generated video"""
        for item in self.generation_history:
            if item.get("scene_id") == video_id:
                return {
                    "status": item.get("status", "unknown"),
                    "video_url": item.get("video_url", ""),
                    "message": f"Status: {item.get('status', 'unknown')}"
                }
        return {"status": "not_found", "message": "Video not found"}
    
    def get_all_video_statuses(self) -> Dict[str, Dict]:
        """Get status of all generated videos"""
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
            "model": self.model,
            "sdk_installed": RUNWAY_SDK_AVAILABLE,
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
        _runway_agent = RunwayVideoAgent()
    return _runway_agent

if __name__ == "__main__":
    agent = RunwayVideoAgent()
    
    print("🎥 Runway Video Agent Status")
    print("=" * 60)
    status = agent.get_status()
    for k, v in status.items():
        print(f"   {k}: {v}")
