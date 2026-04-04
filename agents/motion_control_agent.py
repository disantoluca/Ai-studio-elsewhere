"""
Motion Control Agent

Controls the type of motion/movement in generated videos.
Integrates with video generation by injecting motion-specific prompts.

Supported motion types:
- Subtle Micro-movements: gentle breathing, minimal movement
- Catwalk Turn: runway fashion walk with pivot turn
- Slow 360 Spin: full rotation around model
- Wind + Fabric Movement: static pose with wind effects
- Camera Drift Orbit: cinematic camera movement around static poses
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

MOTION_SNIPPETS = {
    "Subtle Micro-movements": (
        "Very subtle natural motion. The model mostly holds a pose, with gentle breathing, "
        "tiny shifts of weight, and soft fabric sway. No big steps or fast movements."
    ),
    "Catwalk Turn": (
        "Fashion runway motion: the model walks a few steps toward camera, then performs a "
        "clean catwalk-style pivot turn, showing front, three-quarter, and back view. "
        "Movement is confident and controlled."
    ),
    "Slow 360 Spin": (
        "Slow 360-degree spin in place. The model rotates steadily, giving clear views "
        "of front, side, and back of the garment. Motion is smooth and evenly paced."
    ),
    "Wind + Fabric Movement": (
        "Model holds a mostly stable pose while a gentle wind moves hair and fabric. "
        "Focus on the garment's drape, flutter, and texture under light wind."
    ),
    "Camera Drift Orbit": (
        "The model holds 2–3 natural poses while the camera slowly orbits around, "
        "creating a cinematic editorial feel. Motion is smooth and not rushed."
    ),
}


def apply_motion_to_prompt(
    base_prompt: str,
    motion_type: Optional[str],
) -> Tuple[str, Optional[str]]:
    """
    Append a motion-direction block to the prompt based on the selected motion_type.
    
    This function enhances the base prompt with motion-specific instructions
    that control how the model moves in the video.
    
    Args:
        base_prompt: The base prompt (from brand styling, garment classification, etc.)
        motion_type: One of the MOTION_SNIPPETS keys, or None to skip
    
    Returns:
        Tuple of (enhanced_prompt, applied_motion_type_or_None)
        - enhanced_prompt: Base prompt with motion snippet appended
        - applied_motion_type_or_None: The motion type if successfully applied, else None
    
    Example:
        prompt = "Full-body shot of model wearing a shirt..."
        enhanced, applied = apply_motion_to_prompt(prompt, "Catwalk Turn")
        # enhanced now includes motion instructions
        # applied = "Catwalk Turn"
    """
    if not motion_type:
        logger.debug("[MotionAgent] No motion type specified, skipping motion enhancement")
        return base_prompt, None

    snippet = MOTION_SNIPPETS.get(motion_type)
    if not snippet:
        logger.warning(f"[MotionAgent] Unknown motion type: {motion_type}")
        return base_prompt, None

    enhanced = (
        base_prompt
        + "\n\nMotion direction:\n"
        + snippet
    )
    logger.info(f"[MotionAgent] ✅ Applied motion type: {motion_type}")
    return enhanced, motion_type


def get_supported_motions() -> dict:
    """
    Get all supported motion types with their descriptions.
    
    Returns:
        Dictionary mapping motion type names to their descriptions
    """
    return MOTION_SNIPPETS.copy()


def get_motion_status() -> dict:
    """
    Get agent status for debugging/monitoring.
    
    Returns:
        Status dict with supported motions and agent info
    """
    return {
        "agent": "motion_control",
        "enabled": True,
        "supported_motions": list(MOTION_SNIPPETS.keys()),
        "total_motions": len(MOTION_SNIPPETS),
    }
