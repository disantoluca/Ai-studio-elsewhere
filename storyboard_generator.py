#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Storyboard Generator for AI Studio Elsewhere
Converts scenes into cinematic storyboard panels
"""

from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class StoryboardPanel:
    """Single storyboard panel"""
    shot: str
    description: str
    prompt: str
    image_url: Optional[str] = None
    notes: Optional[str] = None
    camera_direction: Optional[str] = None


def get_storyboard_layouts() -> Dict[str, int]:
    """Available storyboard layouts with panel counts"""
    return {
        "6-panel (Standard)": 6,
        "8-panel (Extended)": 8,
        "12-panel (Full Scroll)": 12,
    }


def generate_storyboard(scene: Dict, panel_count: int = 6) -> List[StoryboardPanel]:
    """
    Generate a storyboard from a scene dict.
    
    Args:
        scene: Dict with heading, location, time_of_day, mood, action, visual_prompt, video_prompt
        panel_count: Number of panels (6, 8, or 12)
    
    Returns:
        List of StoryboardPanel objects
    """
    heading = scene.get("heading", "Scene")
    location = scene.get("location", "Unknown")
    time_of_day = scene.get("time_of_day", "Day")
    mood = scene.get("mood", "neutral")
    action = scene.get("action", "")
    visual_prompt = scene.get("visual_prompt", "")
    video_prompt = scene.get("video_prompt", "")
    
    # Base prompt elements
    base_style = f"{location}, {time_of_day}, {mood} atmosphere"
    
    # Shot progression templates
    shot_templates = {
        6: [
            ("Establishing Wide", "Wide establishing shot of the location", "static wide", "Static wide shot"),
            ("Medium Approach", "Camera approaches the subject", "slow dolly in", "Dolly in"),
            ("Character Introduction", "First clear view of the character", "medium shot", "Medium shot, steady"),
            ("Action Beat", "Key moment of action or emotion", "dynamic", "Handheld, following action"),
            ("Reaction / Detail", "Close-up on emotional reaction or detail", "close-up", "Close-up, shallow depth"),
            ("Scene Resolution", "Final moment, transition out", "pull back", "Slow pull back or fade"),
        ],
        8: [
            ("Establishing Wide", "Wide establishing shot of the environment", "static wide", "Static wide shot"),
            ("Environment Detail", "A telling detail of the surroundings", "close detail", "Macro or close-up detail"),
            ("Medium Approach", "Camera approaches the subject", "slow dolly in", "Dolly in"),
            ("Character Introduction", "First clear view of the character", "medium shot", "Medium shot, steady"),
            ("Interaction Beat", "Character interacts with environment", "tracking", "Side tracking shot"),
            ("Emotional Peak", "Key emotional moment", "close-up", "Close-up, shallow depth"),
            ("Reaction / Counter", "Reaction or opposing perspective", "reverse angle", "Reverse angle"),
            ("Scene Resolution", "Final moment, transition out", "pull back", "Slow pull back or fade"),
        ],
        12: [
            ("Pre-Dawn / Atmosphere", "Mood-setting environmental shot", "static wide", "Static, atmospheric"),
            ("Establishing Wide", "Wide establishing shot", "slow pan", "Slow pan across scene"),
            ("Environment Detail A", "First environmental detail", "close detail", "Close-up detail"),
            ("Environment Detail B", "Second environmental detail", "close detail", "Tilt or pan to detail"),
            ("Character Arrival", "Character enters or is revealed", "medium wide", "Medium wide, steady"),
            ("Character Close", "Character in closer framing", "medium", "Medium shot"),
            ("Action Setup", "Building toward key moment", "tracking", "Tracking shot"),
            ("Action Peak", "Key action or dialogue moment", "dynamic", "Dynamic, handheld"),
            ("Emotional Close-Up", "Peak emotional expression", "extreme close-up", "ECU, shallow depth"),
            ("Reaction Beat", "Response or consequence", "medium", "Medium shot, steady"),
            ("Environment Return", "Return to wider view", "pull back", "Dolly out"),
            ("Scene Resolution", "Final image, transition", "static", "Static, fade to black"),
        ],
    }
    
    templates = shot_templates.get(panel_count, shot_templates[6])
    
    panels = []
    for shot_name, description, shot_type, camera in templates:
        # Build a specific prompt for this panel
        prompt = f"{heading}. {base_style}. {shot_type} shot. {description}."
        
        if visual_prompt:
            prompt += f" Visual reference: {visual_prompt[:150]}"
        
        if action and "action" in shot_name.lower():
            prompt += f" Action: {action[:100]}"
        
        panel = StoryboardPanel(
            shot=shot_name,
            description=f"{description} — {location}, {time_of_day}",
            prompt=prompt,
            camera_direction=camera,
        )
        panels.append(panel)
    
    return panels
