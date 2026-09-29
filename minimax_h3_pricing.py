#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiniMax H3 Pricing — versioned, isolated cost-estimation layer.

Deliberately has NO import of minimax_h3_agent, no network access, and no
knowledge of MINIMAX_API_KEY. A rate change here is a data edit, never a
client-code edit — see architecture checkpoint 2026-09-29.

Source: MiniMax Open Platform docs, /docs/guides/pricing-paygo#video
(fetched 2026-09-29). Cross-checked against a user-supplied rate card dated
2026-09-29; the two agree on every figure the card covered. The docs page
additionally distinguishes MiniMax-H3 vs MiniMax-H3-Max reference-asset
rates, which the user's card did not break out — both are recorded below.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

PRICING_SOURCE = "MiniMax Open Platform docs, /docs/guides/pricing-paygo#video"
PRICING_VERSION = "2026-09-29"

# Output, per second, by model + resolution.
OUTPUT_RATE_PER_SECOND: Dict[str, Dict[str, float]] = {
    "MiniMax-H3":     {"768P": 0.08, "2K": 0.13},
    "MiniMax-H3-Max": {"480P": 0.05, "768P": 0.08},
}

# Reference-image pricing: N free, then a flat per-extra-image rate.
IMAGE_REFERENCE_RATE: Dict[str, Dict[str, float]] = {
    "MiniMax-H3":     {"free": 5, "extra_usd": 0.04},
    "MiniMax-H3-Max": {"free": 2, "extra_usd": 0.074},
}

# Reference-video pricing, per second, keyed by the reference clip's OWN resolution.
VIDEO_REFERENCE_RATE_PER_SECOND: Dict[str, Dict[str, float]] = {
    "MiniMax-H3":     {"768P": 0.08, "2K": 0.13},
    "MiniMax-H3-Max": {"480P": 0.0553, "768P": 0.143},
}

# Reference audio is always free for every model / task type.
AUDIO_REFERENCE_RATE_PER_SECOND = 0.0

# Regeneration (768P -> 2K upscale). Reserved for V1.1 — not called from V1 UI.
REGENERATION_OUTPUT_RATE_PER_SECOND = 0.05
REGENERATION_IMAGE_RATE: Dict[str, float] = {"free": 5, "extra_usd": 0.025}
REGENERATION_VIDEO_RATE_PER_SECOND = 0.05

# H3-Context-IR, token-based. Reserved for V1.1 — not called from V1 UI.
CONTEXT_IR_INPUT_USD_PER_M_TOKENS = 0.90
CONTEXT_IR_OUTPUT_USD_PER_M_TOKENS = 3.60


class MiniMaxPricingError(ValueError):
    """Raised for a cost request that pricing data can't answer (unknown model/resolution)."""


@dataclass
class CostLineItem:
    label: str
    amount_usd: float


@dataclass
class CostEstimate:
    total_usd: float
    line_items: List[CostLineItem] = field(default_factory=list)
    pricing_version: str = PRICING_VERSION
    pricing_source: str = PRICING_SOURCE


def estimate_video_cost(
    model: str,
    resolution: str,
    duration_seconds: int,
    num_reference_images: int = 0,
    reference_video_seconds: float = 0.0,
    reference_video_resolution: Optional[str] = None,
) -> CostEstimate:
    """Estimate the cost of a single V1 H3 / H3-Max generation BEFORE
    submission. Does not cover H3-Context-IR or regeneration — see
    estimate_regeneration_cost() / estimate_context_ir_cost(), kept
    separate since neither is exposed in the V1 UI."""
    if model not in OUTPUT_RATE_PER_SECOND:
        raise MiniMaxPricingError(f"Unknown model '{model}'.")
    if resolution not in OUTPUT_RATE_PER_SECOND[model]:
        raise MiniMaxPricingError(f"{model} has no documented rate for resolution '{resolution}'.")
    if duration_seconds <= 0:
        raise MiniMaxPricingError(f"duration_seconds must be positive, got {duration_seconds}.")

    line_items: List[CostLineItem] = []

    output_rate = OUTPUT_RATE_PER_SECOND[model][resolution]
    line_items.append(CostLineItem(
        f"{model} output @ {resolution} x {duration_seconds}s",
        output_rate * duration_seconds,
    ))

    img_rule = IMAGE_REFERENCE_RATE[model]
    billable_images = max(0, num_reference_images - img_rule["free"])
    if billable_images:
        line_items.append(CostLineItem(
            f"{billable_images} reference image(s) beyond free tier",
            billable_images * img_rule["extra_usd"],
        ))

    if reference_video_seconds > 0:
        ref_res = reference_video_resolution or resolution
        video_rates = VIDEO_REFERENCE_RATE_PER_SECOND[model]
        if ref_res not in video_rates:
            raise MiniMaxPricingError(f"{model} has no documented reference-video rate for resolution '{ref_res}'.")
        line_items.append(CostLineItem(
            f"reference video @ {ref_res} x {reference_video_seconds}s",
            video_rates[ref_res] * reference_video_seconds,
        ))

    # Reference audio is always free — no line item, noted here for auditability.

    total = round(sum(li.amount_usd for li in line_items), 4)
    return CostEstimate(total_usd=total, line_items=line_items)


def estimate_regeneration_cost(
    duration_seconds: int,
    original_num_reference_images: int = 0,
    original_reference_video_seconds: float = 0.0,
) -> CostEstimate:
    """768P -> 2K regeneration cost. Reserved for V1.1 — not called from V1 UI."""
    if duration_seconds <= 0:
        raise MiniMaxPricingError(f"duration_seconds must be positive, got {duration_seconds}.")

    line_items = [CostLineItem(
        f"MiniMax-H3-Regeneration output x {duration_seconds}s",
        REGENERATION_OUTPUT_RATE_PER_SECOND * duration_seconds,
    )]
    billable_images = max(0, original_num_reference_images - REGENERATION_IMAGE_RATE["free"])
    if billable_images:
        line_items.append(CostLineItem(
            f"{billable_images} rebilled reference image(s)",
            billable_images * REGENERATION_IMAGE_RATE["extra_usd"],
        ))
    if original_reference_video_seconds > 0:
        line_items.append(CostLineItem(
            f"rebilled reference video x {original_reference_video_seconds}s",
            REGENERATION_VIDEO_RATE_PER_SECOND * original_reference_video_seconds,
        ))
    total = round(sum(li.amount_usd for li in line_items), 4)
    return CostEstimate(total_usd=total, line_items=line_items)


def estimate_context_ir_cost(input_tokens: int, output_tokens: int) -> CostEstimate:
    """Reserved for V1.1 — not called from V1 UI."""
    if input_tokens < 0 or output_tokens < 0:
        raise MiniMaxPricingError("token counts must be non-negative.")
    input_cost = (input_tokens / 1_000_000) * CONTEXT_IR_INPUT_USD_PER_M_TOKENS
    output_cost = (output_tokens / 1_000_000) * CONTEXT_IR_OUTPUT_USD_PER_M_TOKENS
    line_items = [
        CostLineItem(f"H3-Context-IR input ({input_tokens} tokens)", input_cost),
        CostLineItem(f"H3-Context-IR output ({output_tokens} tokens)", output_cost),
    ]
    return CostEstimate(total_usd=round(input_cost + output_cost, 4), line_items=line_items)
