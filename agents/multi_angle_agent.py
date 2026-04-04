"""
Multi-Angle Prompt Generator Agent

Uses:
- BrandStyleAgent (brand_style_agent.build_brand_styled_prompt)
- Garment classifier (indirectly)

Generates angle-specific prompts for fashion image/video generation.

Supported angles:
- front: Full frontal view
- three_quarter: 45-degree angle
- side: Strict side profile
- back: Rear view

Can be used for:
1. Multi-angle still image generation (4 product photos)
2. Multi-angle video generation (4 short clips)
3. 360-degree lookbook sequences
"""

import logging
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)

# Try to import brand style agent
try:
    from app.agents.brand_style_agent import build_brand_styled_prompt
    BRAND_AGENT_AVAILABLE = True
except ImportError:
    BRAND_AGENT_AVAILABLE = False
    logger.warning("⚠️ Could not import brand_style_agent. Make sure it exists.")


# ================================================================ #
# ANGLE-SPECIFIC CAMERA & POSE DIRECTIONS
# ================================================================ #

ANGLE_SNIPPETS: Dict[str, str] = {
    "front": """
Camera angle: full frontal view, camera at chest height.
The model faces directly toward the camera.
Both shoulders and legs visible symmetrically.
The goal is to clearly show the front of the garment: neckline, front closure, print, and overall silhouette.
""".strip(),

    "three_quarter": """
Camera angle: three-quarter view (about 45 degrees).
The model turns slightly so one shoulder is closer to camera.
This angle highlights garment depth, drape along the side, and silhouette from front to side.
""".strip(),

    "side": """
Camera angle: strict side profile.
The model stands perpendicular to the camera, with one shoulder pointing toward the lens.
This angle emphasizes garment side seam, shoulder line, sleeve shape, and leg profile (for pants/skirts).
""".strip(),

    "back": """
Camera angle: rear view.
The model faces away from the camera, with back fully visible.
This angle showcases back construction: seams, closures, vents, pleats, and back silhouette.
""".strip(),
}


class MultiAngleAgent:
    """
    Agent that generates angle-specific prompts for multi-view fashion content.
    
    Reuses BrandStyleAgent to get garment + brand tuning, then layers camera angles on top.
    """

    def __init__(self):
        """Initialize Multi-Angle Agent."""
        self.enabled = BRAND_AGENT_AVAILABLE
        
        if self.enabled:
            logger.info("✅ MultiAngleAgent initialized")
        else:
            logger.warning("⚠️ MultiAngleAgent initialized (BrandStyleAgent not available)")

    def get_angle_snippet(self, angle: str) -> Optional[str]:
        """
        Get angle-specific camera direction.
        
        Args:
            angle: "front", "three_quarter", "side", or "back"
        
        Returns:
            Angle-specific camera direction text or None if angle not recognized
        """
        return ANGLE_SNIPPETS.get(angle.lower())

    def build_multi_angle_prompts(
        self,
        image_url: str,
        brand: Optional[str] = None,
        notes: Optional[str] = None,
        angles: Optional[list] = None,
    ) -> Tuple[Dict[str, str], str]:
        """
        Build brand-styled, garment-aware prompts for multiple angles.

        Pipeline:
        1. Use BrandStyleAgent to get base prompt (garment + brand)
        2. Layer angle-specific camera instructions
        3. Return dict of prompts indexed by angle

        Args:
            image_url: URL of the garment image to classify
            brand: Optional brand style (e.g., "zara", "cos", "gucci")
            notes: Optional designer notes
            angles: Subset of ["front", "three_quarter", "side", "back"].
                    If None, all 4 angles are generated.

        Returns:
            Tuple of (prompts_by_angle, garment_type)
            where prompts_by_angle is:
            {
              "front": "<full optimized prompt>",
              "three_quarter": "<full optimized prompt>",
              "side": "<full optimized prompt>",
              "back": "<full optimized prompt>",
            }
        """

        if not self.enabled:
            logger.warning("[MultiAngleAgent] BrandStyleAgent not available")
            return {}, "unknown"

        if angles is None:
            angles = ["front", "three_quarter", "side", "back"]

        logger.info(
            f"[MultiAngleAgent] Building multi-angle prompts"
        )
        logger.info(f"  - Image: {image_url}")
        logger.info(f"  - Brand: {brand or 'generic_editorial'}")
        logger.info(f"  - Angles: {angles}")

        # Step 1: Get base brand-styled prompt
        logger.info("[MultiAngleAgent] Step 1: Getting base brand-styled prompt")
        
        base_prompt, garment_type = build_brand_styled_prompt(
            image_source=image_url,
            brand=brand,
            notes=notes,
        )

        logger.info(f"[MultiAngleAgent] ✅ Base prompt built for garment_type={garment_type}")

        # Step 2: Layer angle-specific instructions
        prompts_by_angle: Dict[str, str] = {}

        logger.info("[MultiAngleAgent] Step 2: Layering angle-specific instructions")

        for angle in angles:
            angle_lower = angle.lower().strip()
            snippet = self.get_angle_snippet(angle_lower)

            if not snippet:
                logger.warning(f"[MultiAngleAgent] Unknown angle key: {angle}")
                continue

            # Combine base prompt + angle instruction
            full_prompt = f"{base_prompt}\n\nCamera angle and pose direction:\n{snippet}"
            prompts_by_angle[angle_lower] = full_prompt

            logger.info(f"[MultiAngleAgent] ✅ Built prompt for angle: {angle_lower}")

        logger.info(
            f"[MultiAngleAgent] ✅ Generated {len(prompts_by_angle)} angle prompts "
            f"for garment={garment_type}, brand={brand or 'generic_editorial'}"
        )

        return prompts_by_angle, garment_type

    def get_status(self) -> dict:
        """Get agent status for debugging."""
        return {
            "agent": "multi_angle",
            "enabled": self.enabled,
            "brand_agent_available": BRAND_AGENT_AVAILABLE,
            "supported_angles": list(ANGLE_SNIPPETS.keys()),
        }


# ====================================================================
# Singleton factory
# ====================================================================

_agent_instance: Optional[MultiAngleAgent] = None


def get_multi_angle_agent() -> MultiAngleAgent:
    """Get or create MultiAngleAgent singleton."""
    global _agent_instance

    if _agent_instance is None:
        _agent_instance = MultiAngleAgent()

    return _agent_instance


# ====================================================================
# Convenience functions
# ====================================================================

def build_multi_angle_prompts(
    image_url: str,
    brand: Optional[str] = None,
    notes: Optional[str] = None,
    angles: Optional[list] = None,
) -> Tuple[Dict[str, str], str]:
    """
    Quick pipeline for multi-angle prompt generation.
    
    Args:
        image_url: URL to garment image
        brand: Brand name (optional)
        notes: Designer notes (optional)
        angles: List of angle keys (optional, defaults to all 4)
    
    Returns:
        Tuple of (prompts_by_angle, garment_type)
    """
    agent = get_multi_angle_agent()
    return agent.build_multi_angle_prompts(iimage_source,brand, notes, angles)


def get_supported_angles() -> list:
    """Get list of supported camera angles."""
    return list(ANGLE_SNIPPETS.keys())


def get_angle_snippet(angle: str) -> Optional[str]:
    """Get camera direction for a specific angle."""
    agent = get_multi_angle_agent()
    return agent.get_angle_snippet(angle)
