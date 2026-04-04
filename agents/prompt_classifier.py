"""
Garment Prompt Classifier Agent

Tasks:
1. Classify garment category from input image URL (simple heuristic or vision model placeholder)
2. Build a fashion-movement + fit-focused prompt for video generation
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1. Very simple garment classifier (placeholder)
# ----------------------------------------------------------------------

def classify_garment(image_url: str) -> str:
    """
    Very lightweight garment classifier.
    Replace with real vision model later.

    Returns:
        One of:
            "dress", "coat", "t-shirt", "shirt", "pants",
            "skirt", "jacket", "suit", "unknown"
    """
    url = image_url.lower()

    # filename / path heuristics
    if "dress" in url:
        return "dress"
    if "coat" in url:
        return "coat"
    if "jacket" in url:
        return "jacket"
    if "skirt" in url:
        return "skirt"
    if "pants" in url or "trousers" in url:
        return "pants"
    if "shirt" in url or "tshirt" in url or "t-shirt" in url:
        return "shirt"
    if "suit" in url:
        return "suit"

    logger.warning(f"[GarmentClassifier] Unable to detect garment from URL: {image_url}")
    return "unknown"


# ----------------------------------------------------------------------
# 2. Prompt templates per garment
# ----------------------------------------------------------------------

GARMENT_PROMPTS = {
    "dress": """
Full-body studio shot. A model wearing a flowing dress. Show realistic fabric movement, light swaying,
and gentle natural motion. Focus on drape, silhouette, and hem dynamics. Camera is steady, neutral,
and editorial style.
""",

    "coat": """
Model wearing a structured coat. Subtle body turns show the shoulder line, collar structure, and material weight.
Emphasize texture, stitching, and the way the coat opens and closes with motion. Clean runway lighting.
""",

    "shirt": """
A model wearing a shirt. Light natural movements: small steps, arm adjustments, soft turns.
Emphasize collar structure, sleeve fit, and fabric creases. Clean product-focused framing.
""",

    "pants": """
Model wearing tailored pants. Show waistline, hip fit, and leg shape with smooth walking-motion loops.
Focus on fabric tension, folds, and silhouette stability. Neutral studio environment.
""",

    "skirt": """
Model wearing a skirt. Gentle spinning or stepping motion to reveal hem flow and drape.
Soft fabric behavior, natural sway, and clean editorial camera work.
""",

    "jacket": """
Editorial shot of a model wearing a jacket. Highlight structure, seams, and material density.
Subtle body turns to show the silhouette from multiple angles. Neutral lighting.
""",

    "suit": """
Model in a full suit. Cinematic but clean movement: small steps, head turn, jacket buttoning motion.
Focus on tailoring lines, fit, and premium fabric behavior.
""",

    "unknown": """
Full-body neutral fashion pose. Clean studio background. Natural subtle movement loop.
Focus on garment fit, silhouette, and realistic texture rendering.
""",
}


# ----------------------------------------------------------------------
# 3. Build a final movement/fit prompt for the given garment
# ----------------------------------------------------------------------

def build_prompt_for_garment(
    garment_type: str,
    notes: Optional[str] = None
) -> str:
    """
    Constructs the garment-specific movement and fit prompt.

    Args:
        garment_type: detected garment
        notes: optional user notes to append

    Returns:
        A single full prompt string
    """
    garment_type = garment_type.lower().strip()
    base_prompt = GARMENT_PROMPTS.get(garment_type, GARMENT_PROMPTS["unknown"])

    if notes:
        return f"{base_prompt}\n\nExtra designer notes: {notes}"

    return base_prompt
