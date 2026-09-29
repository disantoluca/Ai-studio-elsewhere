#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiniMax H3 Video Generation UI Component
For AI Studio Elsewhere

Deliberately its own module — NOT folded into runway_video_ui.py — so the
working Runway UI stays untouched. Provider choice lives one level up, in
ai_studio_elsewhere.py's tab_video block. See architecture checkpoint
2026-09-29.

V1 scope only: text-to-video, image-to-video (first frame), reference-to-
video (reference image). H3-Context-IR and 2K regeneration are NOT exposed
here.
"""

import base64
import logging
from pathlib import Path
from typing import Dict, List

import streamlit as st

logger = logging.getLogger(__name__)

try:
    from minimax_h3_agent import (
        ContentItem,
        MODEL_DURATION_RANGE,
        MODEL_RESOLUTIONS,
        MODELS,
        VALID_RATIOS,
        VideoGenRequest,
        detect_audio_stream,
        get_minimax_h3_agent,
    )
    MINIMAX_H3_AVAILABLE = True
except ImportError:
    MINIMAX_H3_AVAILABLE = False
    logger.warning("⚠️ MiniMax H3 agent not available")

try:
    from minimax_h3_pricing import PRICING_SOURCE, PRICING_VERSION, MiniMaxPricingError, estimate_video_cost
    MINIMAX_PRICING_AVAILABLE = True
except ImportError:
    MINIMAX_PRICING_AVAILABLE = False


def _safe_path_exists(p: str) -> bool:
    """Path.exists() that never raises — guards against data URIs / long strings."""
    try:
        return Path(p).exists()
    except OSError:
        return False


_AUDIO_LABELS = {
    True: "🔊 audio stream detected",
    False: "🔇 no audio stream detected",
    None: "❔ audio presence not established",
}


def _usd(amount: float) -> str:
    """Display-only USD formatting — two decimals, no bare API-style
    4-decimal values. Never touches the underlying stored/estimated float,
    which keeps its full precision in `cost`/`GenerationRecord`."""
    return f"${amount:.2f} USD"


def display_minimax_h3_tab(scenes: List[Dict], project_title: str):
    """MiniMax H3 video generation — V1 scope only."""
    if not MINIMAX_H3_AVAILABLE or not MINIMAX_PRICING_AVAILABLE:
        st.error("❌ MiniMax H3 module not loaded — check minimax_h3_agent.py / minimax_h3_pricing.py")
        return

    st.header("🌀 MiniMax H3")
    st.caption(f"Pricing source: {PRICING_SOURCE} · version {PRICING_VERSION}")

    if not scenes:
        st.warning("⚠️ No scenes available. Extract scenes first.")
        return

    agent = get_minimax_h3_agent()
    if not agent.available:
        st.warning("⚠️ MiniMax API not configured. Add MINIMAX_API_KEY (Railway env var or sidebar field).")
        return

    scene_options = {f"Scene {i+1}: {s.get('heading', 'Untitled')}": i for i, s in enumerate(scenes)}
    selected_label = st.selectbox("Select Scene", list(scene_options.keys()), key="mmh3_scene")
    scene = scenes[scene_options[selected_label]]

    concept_path = scene.get("concept_image") or scene.get("concept_image_path")
    if isinstance(concept_path, str) and concept_path.startswith("data:image/"):
        try:
            st.image(base64.b64decode(concept_path.split(",", 1)[1]), width=400, caption="Reference frame")
        except Exception:
            pass
    elif isinstance(concept_path, str) and _safe_path_exists(concept_path):
        st.image(concept_path, width=400, caption="Reference frame")

    col1, col2 = st.columns(2)
    with col1:
        model = st.selectbox("Model", MODELS, key="mmh3_model")
    with col2:
        allowed_res = sorted(MODEL_RESOLUTIONS[model])
        resolution = st.selectbox("Resolution", allowed_res, key="mmh3_resolution")

    lo, hi = MODEL_DURATION_RANGE[model]
    duration = st.slider("Duration (seconds)", lo, hi, lo, key="mmh3_duration")
    ratio = st.selectbox("Aspect ratio", sorted(VALID_RATIOS), key="mmh3_ratio")

    prompt = st.text_area("Prompt", value=scene.get("prompt", ""), height=100, key="mmh3_prompt")

    mode_choice = st.radio(
        "Generation mode",
        ["Text-to-video", "Image-to-video (first frame)", "Reference-to-video (reference image)"],
        key="mmh3_mode",
    )

    reference_assets: List[ContentItem] = []
    concept_is_public_url = isinstance(concept_path, str) and concept_path.startswith(("http://", "https://"))
    if mode_choice != "Text-to-video":
        if concept_is_public_url:
            role = "first_frame" if mode_choice.startswith("Image-to-video") else "reference_image"
            reference_assets.append(ContentItem(type="image_url", url=concept_path, role=role))
            st.caption(f"Using this scene's concept image as `{role}`.")
        else:
            st.info(
                "This scene has no public-URL concept image (local files / inline base64 "
                "aren't submitted automatically in V1), so this generation will run as "
                "text-to-video instead."
            )

    try:
        cost = estimate_video_cost(
            model=model,
            resolution=resolution,
            duration_seconds=duration,
            num_reference_images=1 if reference_assets else 0,
        )
    except MiniMaxPricingError as e:
        st.error(f"Pricing error: {e}")
        return

    st.markdown(f"### Estimated cost: **{_usd(cost.total_usd)}**")
    with st.expander("Cost breakdown", expanded=False):
        st.write(f"**{model} · {resolution}**")
        for i, li in enumerate(cost.line_items):
            if i == 0 and duration:
                # Primary output line — show the underlying per-second rate,
                # not just the label, for a director-legible breakdown.
                per_second = li.amount_usd / duration
                st.write(f"- {duration} sec × ${per_second:.2f}/sec = {_usd(li.amount_usd)}")
            else:
                st.write(f"- {li.label}: {_usd(li.amount_usd)}")
        st.write(f"**Estimated total: {_usd(cost.total_usd)}**")

    confirm = st.checkbox(
        f"I understand this will call the paid MiniMax API for an estimated {_usd(cost.total_usd)}.",
        key="mmh3_confirm",
    )

    if st.button("🌀 Generate with MiniMax H3", type="primary", disabled=not confirm, key="mmh3_generate"):
        request = VideoGenRequest(
            prompt=prompt,
            model=model,
            resolution=resolution,
            duration=duration,
            ratio=ratio,
            reference_assets=reference_assets,
        )
        with st.spinner("Submitting to MiniMax H3 and polling for completion — this can take a few minutes..."):
            record = agent.generate_video(
                request,
                pricing_version=cost.pricing_version,
                estimated_cost_usd=cost.total_usd,
            )
            if record.status == "succeeded" and record.output_url:
                record.audio_present = detect_audio_stream(record.output_url)

        if record.status == "succeeded":
            st.success(f"✅ Generation succeeded — task {record.task_id}")
            if record.output_url:
                st.video(record.output_url)
                st.caption("Remote MiniMax result URL — not a durable local asset in V1.")
            st.caption(_AUDIO_LABELS[record.audio_present])
        elif record.status == "timeout":
            st.warning(f"⏱️ Timed out waiting for task {record.task_id}: {record.error}")
        else:
            st.error(f"❌ Generation {record.status}: {record.error}")

    if agent.generation_history:
        st.markdown("---")
        st.markdown("#### Generation history")
        for rec in reversed(agent.generation_history[-10:]):
            with st.expander(f"{rec.created_at} — {rec.model} — {rec.status}"):
                st.json(rec.to_safe_dict())
