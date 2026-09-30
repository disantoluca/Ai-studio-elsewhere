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
import mimetypes
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import streamlit as st

logger = logging.getLogger(__name__)

try:
    from sequence_assembly import (
        MaterializationError,
        Sequence,
        SequenceAssemblyError,
        SequenceShot,
        SelectedTake,
        assemble_sequence,
        register_local_file,
    )
    SEQUENCE_ASSEMBLY_AVAILABLE = True
except ImportError:
    SEQUENCE_ASSEMBLY_AVAILABLE = False
    logger.warning("⚠️ sequence_assembly not available")

try:
    from minimax_h3_agent import (
        ContentItem,
        MAX_REFERENCE_IMAGES,
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


def _history_entry_title(rec) -> str:
    """Generation History expander title. `shot_label` is display-only
    metadata for telling shots apart in a sequence — when present it's
    shown first, but created_at/status/model stay visible too, and
    task_id (the real technical identity) remains available inside the
    expanded JSON either way. When absent, preserves the original title
    exactly as before this feature existed."""
    if rec.shot_label:
        return f"{rec.shot_label} — {rec.status} · {rec.model} · {rec.created_at}"
    return f"{rec.created_at} — {rec.model} — {rec.status}"


# ── Reference-image normalization ───────────────────────────────────────────
# Verified 2026-09-30 against platform.minimax.io/docs/api-reference/
# video-generation-v2-create: image_url.url officially accepts a public URL,
# `mm_file://{file_id}`, OR a `data:image/<format>;base64,<Base64>` data URI.
# minimax_h3_agent.py's ContentItem/validate_request already pass any
# non-empty url string through untouched — only this UI layer previously
# restricted candidates to http(s):// only. One shared path below now covers
# the scene concept image AND an uploaded file, so there is exactly one
# implementation, not two.

# Documented single-file limit (input media limits table).
MAX_REFERENCE_IMAGE_BYTES = 30 * 1024 * 1024

# MIME types Streamlit's uploader + st.image can reliably accept/preview.
# MiniMax's docs additionally list HEIC/HEIF as supported, but those aren't
# previewable here without an extra Pillow plugin — not offered in the
# uploader's type filter, so this is a known, deliberate gap, not a silent one.
_ALLOWED_MIME_TO_FORMAT = {
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/webp": "webp",
}


def _encode_data_uri(raw: bytes, fmt: str) -> Tuple[Optional[str], Optional[str]]:
    if len(raw) > MAX_REFERENCE_IMAGE_BYTES:
        mb = len(raw) / (1024 * 1024)
        return None, f"Image is {mb:.1f} MB — exceeds MiniMax's 30 MB per-file limit."
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:image/{fmt};base64,{b64}", None


def _normalize_reference_image(source) -> Tuple[Optional[str], Optional[str]]:
    """Convert a reference-image source into a MiniMax-ready string, or
    return an error explaining why it can't be used. Never makes a network
    call; never returns/logs the raw image bytes.

    Accepts:
      - an existing public http(s):// URL or data:image/ URI (str) -> passthrough
      - a local filesystem path (str) -> read + base64-encode, if the file
        still exists (it may not, if lost to ephemeral storage)
      - a Streamlit UploadedFile (has .type and .getvalue())

    Returns (result_url, error_message) — exactly one is not None.
    """
    if source is None:
        return None, "No image provided."

    if isinstance(source, str):
        if source.startswith(("http://", "https://", "data:image/")):
            return source, None
        if _safe_path_exists(source):
            try:
                raw = Path(source).read_bytes()
            except OSError as e:
                return None, f"Could not read local file: {e}"
            mime, _ = mimetypes.guess_type(source)
            fmt = _ALLOWED_MIME_TO_FORMAT.get(mime or "")
            if not fmt:
                return None, f"Unsupported image format for '{source}' (allowed: PNG, JPEG, WEBP)."
            return _encode_data_uri(raw, fmt)
        return None, (
            "This local reference image is no longer available — it may have "
            "been lost to ephemeral storage after a deployment."
        )

    # Streamlit UploadedFile
    mime = getattr(source, "type", None)
    fmt = _ALLOWED_MIME_TO_FORMAT.get(mime or "")
    if not fmt:
        return None, f"Unsupported upload type '{mime}' (allowed: PNG, JPEG, WEBP)."
    return _encode_data_uri(source.getvalue(), fmt)


# ── MiniMax-native Shot Sequence ────────────────────────────────────────────
# Additive workflow, separate from Runway's "Shot Sequence"/"Shot Control
# Panel" (runway_video_ui.py, Director Mode) — deliberately not shared code
# and runway_video_ui.py is not touched. Each MiniMax shot owns its own
# label/prompt/camera/lighting/references; a shot is generated independently
# through the exact same MiniMaxH3Agent.generate_video() path as the
# single-shot workflow above. No sequence rendering/composition, transitions,
# take management, or cross-shot reference inheritance in V1 — a sequence
# here is simply an ordered list of independently controllable shots.

def _compose_shot_prompt(base_prompt: str, camera_direction: str = "", lighting_direction: str = "") -> str:
    """Camera/lighting are prose hints, not MiniMax API fields — MiniMax has
    no such structured parameters (confirmed against the verified v2
    contract). They're appended into the same free-text prompt, matching
    how real Blue Tears prompts already embed 'Camera: ...' / 'Lighting: ...'
    sections by hand."""
    parts = []
    if base_prompt and base_prompt.strip():
        parts.append(base_prompt.strip())
    if camera_direction and camera_direction.strip():
        parts.append(f"Camera: {camera_direction.strip()}")
    if lighting_direction and lighting_direction.strip():
        parts.append(f"Lighting: {lighting_direction.strip()}")
    return "\n\n".join(parts)


def _build_shot_reference_assets(image_sources: List) -> Tuple[List[ContentItem], List[str]]:
    """Normalize ONE shot's own image sources into reference_image
    ContentItems. Takes only this shot's sources as a parameter — no access
    to any other shot's data exists in this function's scope, so cross-shot
    leakage is structurally impossible, not merely avoided by convention.
    Returns (assets, error_messages); silently-dropped-without-a-reason
    never happens — every rejected source produces a message."""
    assets: List[ContentItem] = []
    errors: List[str] = []
    for source in image_sources[:MAX_REFERENCE_IMAGES]:
        url, err = _normalize_reference_image(source)
        if url:
            assets.append(ContentItem(type="image_url", url=url, role="reference_image"))
        else:
            name = getattr(source, "name", str(source))
            errors.append(f"{name}: {err}")
    return assets, errors


def _generate_shot(
    agent,
    model: str,
    resolution: str,
    duration: int,
    ratio: str,
    shot_label: str,
    base_prompt: str,
    camera_direction: str,
    lighting_direction: str,
    image_sources: List,
    pricing_version: Optional[str],
    estimated_cost_usd: Optional[float],
):
    """Generate exactly one shot. Every argument describes THIS shot only —
    there is no parameter through which another shot's prompt/label/images
    could reach this call. Does not alter the MiniMax API contract, polling,
    audio detection, or pricing — delegates straight to the same
    MiniMaxH3Agent.generate_video() the single-shot workflow already uses."""
    prompt = _compose_shot_prompt(base_prompt, camera_direction, lighting_direction)
    reference_assets, _errors = _build_shot_reference_assets(image_sources)
    request = VideoGenRequest(
        prompt=prompt,
        model=model,
        resolution=resolution,
        duration=duration,
        ratio=ratio,
        reference_assets=reference_assets,
    )
    return agent.generate_video(
        request,
        pricing_version=pricing_version,
        estimated_cost_usd=estimated_cost_usd,
        shot_label=shot_label,
    )


def _new_shot(label_hint: str = "") -> Dict:
    return {
        "id": str(uuid.uuid4()),
        "label": label_hint,
        "prompt": "",
        "camera": "",
        "lighting": "",
    }


def _selected_take_from_generation_record(rec) -> "SelectedTake":
    """The one place a MiniMax GenerationRecord is read into the
    provider-neutral SelectedTake shape. Only ever reads fields off `rec`
    -- never mutates it. A Runway equivalent would be an equally small,
    separate function; sequence_assembly.py itself never needs to know
    either provider exists."""
    return SelectedTake(
        provider=rec.provider,
        task_id=rec.task_id or "",
        source_url=rec.output_url or "",
        duration_seconds=float(rec.duration_seconds),
        shot_label_hint=rec.shot_label or "",
        audio_present=rec.audio_present,
    )


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

    workflow = st.radio(
        "Workflow", ["Single shot", "Shot Sequence"], key="mmh3_workflow", horizontal=True
    )
    if workflow == "Shot Sequence":
        _display_shot_sequence(agent)
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
    if mode_choice != "Text-to-video":
        role = "first_frame" if mode_choice.startswith("Image-to-video") else "reference_image"
        # Only "reference_image" supports multiple images (documented cap:
        # MAX_REFERENCE_IMAGES). first_frame/last_frame are capped at 1 each
        # regardless, so multi-upload is never offered for that mode.
        allow_multi = role == "reference_image"

        ref_source_choice = st.radio(
            "Reference source",
            ["Scene concept image", "Upload image"],
            key="mmh3_ref_source",
            horizontal=True,
        )

        image_sources: List = []
        if ref_source_choice == "Scene concept image":
            if concept_path:
                image_sources = [concept_path]
            else:
                st.info("This scene has no concept image yet.")
        elif allow_multi:
            uploaded_files = st.file_uploader(
                "Reference images",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
                key="mmh3_upload_multi",
                help=(
                    f"Select several images at once (⌘/Ctrl-click in the file picker, "
                    f"or drag multiple files onto this box). Up to {MAX_REFERENCE_IMAGES} "
                    f"images total — you can also click the '+' after your first upload "
                    f"to add more."
                ),
            )
            st.caption(
                f"💡 Select multiple images at once (⌘/Ctrl-click in the file picker), or "
                f"upload one then click **+** to add more — up to {MAX_REFERENCE_IMAGES} total."
            )
            if uploaded_files:
                if len(uploaded_files) > MAX_REFERENCE_IMAGES:
                    st.warning(
                        f"⚠️ {len(uploaded_files)} files selected — MiniMax allows at most "
                        f"{MAX_REFERENCE_IMAGES} reference images. Only the first "
                        f"{MAX_REFERENCE_IMAGES} will be used."
                    )
                image_sources = list(uploaded_files[:MAX_REFERENCE_IMAGES])
                preview_cols = st.columns(min(len(image_sources), 5))
                for i, f in enumerate(image_sources):
                    with preview_cols[i % len(preview_cols)]:
                        st.image(f, width=150, caption=f.name)
        else:
            uploaded = st.file_uploader(
                "Reference image", type=["png", "jpg", "jpeg", "webp"], key="mmh3_upload"
            )
            if uploaded is not None:
                st.image(uploaded, width=300, caption="Will be used as reference (preview)")
                image_sources = [uploaded]

        for source in image_sources:
            resolved_url, error = _normalize_reference_image(source)
            if resolved_url:
                reference_assets.append(ContentItem(type="image_url", url=resolved_url, role=role))
            else:
                name = getattr(source, "name", str(source))
                st.warning(f"⚠️ Skipped '{name}': {error}")

        if image_sources and not reference_assets:
            st.info("None of the selected image(s) could be used. This generation will run as text-to-video instead.")
        elif reference_assets:
            st.caption(f"Using {len(reference_assets)} image(s) as `{role}`.")

    shot_label = st.text_input(
        "Shot label (optional)",
        key="mmh3_shot_label",
        placeholder="e.g. Shot 02 — Gather & Rise",
        help=(
            "Human-readable metadata for telling generations apart in a "
            "multi-shot sequence. Purely for display in Generation History — "
            "the task ID underneath remains the real technical identity, and "
            "this is never sent to MiniMax as part of the request."
        ),
    ).strip() or None

    try:
        cost = estimate_video_cost(
            model=model,
            resolution=resolution,
            duration_seconds=duration,
            num_reference_images=len(reference_assets),
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
                shot_label=shot_label,
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
            with st.expander(_history_entry_title(rec)):
                st.json(rec.to_safe_dict())


def _display_shot_sequence(agent):
    """MiniMax-native Shot Sequence — additive to, not a replacement for,
    the single-shot workflow above. V1: an ordered list of independently
    controllable shots, each generated on its own. No composition/
    rendering, transitions, take management, or automatic cross-shot
    reference inheritance — continuity across shots is an explicit
    director choice made by re-uploading the same reference(s), not
    something this UI does automatically."""
    st.subheader("Shot Sequence")
    st.caption(
        "Each shot owns its own label, prompt, camera/lighting notes, and reference "
        "images. Generation happens per shot — sequence assembly isn't built yet."
    )

    if "mmh3_shots" not in st.session_state:
        st.session_state["mmh3_shots"] = [_new_shot("Shot 01")]
    shots = st.session_state["mmh3_shots"]

    col1, col2 = st.columns(2)
    with col1:
        model = st.selectbox("Model", MODELS, key="mmh3_seq_model")
    with col2:
        allowed_res = sorted(MODEL_RESOLUTIONS[model])
        resolution = st.selectbox("Resolution", allowed_res, key="mmh3_seq_resolution")
    lo, hi = MODEL_DURATION_RANGE[model]
    duration = st.slider("Duration (seconds)", lo, hi, lo, key="mmh3_seq_duration")
    ratio = st.selectbox("Aspect ratio", sorted(VALID_RATIOS), key="mmh3_seq_ratio")

    shot_to_remove = None
    for i, shot in enumerate(shots):
        sid = shot["id"]
        with st.expander(shot["label"] or f"Shot {i+1}", expanded=True):
            shot["label"] = st.text_input("Shot label", value=shot["label"], key=f"mmh3_seq_label_{sid}")
            shot["prompt"] = st.text_area("Prompt", value=shot["prompt"], height=100, key=f"mmh3_seq_prompt_{sid}")
            c1, c2 = st.columns(2)
            with c1:
                shot["camera"] = st.text_input(
                    "Camera direction (optional)", value=shot["camera"], key=f"mmh3_seq_camera_{sid}"
                )
            with c2:
                shot["lighting"] = st.text_input(
                    "Lighting direction (optional)", value=shot["lighting"], key=f"mmh3_seq_lighting_{sid}"
                )

            uploaded_files = st.file_uploader(
                "Reference images (optional, this shot only)",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
                key=f"mmh3_seq_upload_{sid}",
                help=f"Up to {MAX_REFERENCE_IMAGES} images for this shot only — never shared with other shots.",
            )
            image_sources = list(uploaded_files[:MAX_REFERENCE_IMAGES]) if uploaded_files else []
            if uploaded_files and len(uploaded_files) > MAX_REFERENCE_IMAGES:
                st.warning(f"⚠️ Only the first {MAX_REFERENCE_IMAGES} images will be used.")

            reference_assets, ref_errors = _build_shot_reference_assets(image_sources)
            for err in ref_errors:
                st.warning(f"⚠️ Skipped {err}")
            if image_sources:
                preview_cols = st.columns(min(len(image_sources), 5))
                for j, f in enumerate(image_sources):
                    with preview_cols[j % len(preview_cols)]:
                        st.image(f, width=120, caption=f.name)

            try:
                cost = estimate_video_cost(
                    model=model, resolution=resolution, duration_seconds=duration,
                    num_reference_images=len(reference_assets),
                )
            except MiniMaxPricingError as e:
                st.error(f"Pricing error: {e}")
                cost = None

            if cost is not None:
                st.markdown(f"**Estimated cost: {_usd(cost.total_usd)}**")
                confirm = st.checkbox(
                    f"I understand this will call the paid MiniMax API for an estimated {_usd(cost.total_usd)}.",
                    key=f"mmh3_seq_confirm_{sid}",
                )
                if st.button(
                    f"🌀 Generate {shot['label'] or f'Shot {i+1}'}",
                    type="primary", disabled=not confirm, key=f"mmh3_seq_generate_{sid}",
                ):
                    with st.spinner("Submitting to MiniMax H3 and polling for completion..."):
                        record = _generate_shot(
                            agent,
                            model=model, resolution=resolution, duration=duration, ratio=ratio,
                            shot_label=shot["label"] or f"Shot {i+1}",
                            base_prompt=shot["prompt"], camera_direction=shot["camera"],
                            lighting_direction=shot["lighting"], image_sources=image_sources,
                            pricing_version=cost.pricing_version, estimated_cost_usd=cost.total_usd,
                        )
                        if record.status == "succeeded" and record.output_url:
                            record.audio_present = detect_audio_stream(record.output_url)

            # Looked up from agent.generation_history on every render (not
            # gated behind the button's transient True return) so this
            # shot's result stays visible across reruns triggered elsewhere
            # on the page -- e.g. adding another shot no longer makes this
            # shot's result disappear.
            shot_label_for_lookup = shot["label"] or f"Shot {i+1}"
            shot_records = [r for r in agent.generation_history if r.shot_label == shot_label_for_lookup]
            if shot_records:
                latest = shot_records[-1]
                st.markdown(f"**Latest result — task {latest.task_id}:**")
                if latest.status == "succeeded":
                    st.success(f"✅ Succeeded — task {latest.task_id}")
                    if latest.output_url:
                        st.video(latest.output_url)
                        st.caption("Remote MiniMax result URL — not a durable local asset in V1.")
                    st.caption(_AUDIO_LABELS[latest.audio_present])
                elif latest.status == "timeout":
                    st.warning(f"⏱️ Timed out: {latest.error}")
                else:
                    st.error(f"❌ {latest.status}: {latest.error}")

            if st.button("🗑️ Remove this shot", key=f"mmh3_seq_remove_{sid}"):
                shot_to_remove = sid

    if shot_to_remove is not None:
        st.session_state["mmh3_shots"] = [s for s in shots if s["id"] != shot_to_remove]
        st.rerun()

    if st.button("+ Add Shot", key="mmh3_seq_add_shot"):
        st.session_state["mmh3_shots"].append(_new_shot(f"Shot {len(shots) + 1:02d}"))
        st.rerun()

    if agent.generation_history:
        st.markdown("---")
        st.markdown("#### Generation history")
        for rec in reversed(agent.generation_history[-10:]):
            with st.expander(_history_entry_title(rec)):
                st.json(rec.to_safe_dict())

    _display_sequence_assembly(agent)


def _display_sequence_assembly(agent):
    """Sequence Assembly V1 — additive, beneath Shot Sequence. Its state
    (st.session_state["mmh3_sequence_shots"]) is deliberately separate from
    the generation-control state (mmh3_shots): choosing a take/trim here
    never touches a shot's prompt/camera/lighting/references, and never
    mutates any GenerationRecord. sequence_assembly.py itself has no
    Streamlit/MiniMax knowledge at all -- everything provider-specific
    happens in this function via _selected_take_from_generation_record().

    A shot's take can come from either agent.generation_history (this
    session's live generations) OR a local file upload. The upload path
    exists because agent.generation_history is process-memory-only and
    does not survive a Railway redeploy (2026-09-30) -- uploading a
    previously-downloaded clip is the recovery path when a session
    resets but the actual video files are still safe on disk."""
    st.markdown("---")
    st.subheader("Sequence Assembly")
    st.caption(
        "Choose which generated take belongs to each shot, set in/out trims, preview, "
        "and export one MP4. Hard cuts only — no transitions, titles, music, or color "
        "grading in V1. Source audio is always preserved."
    )

    if not SEQUENCE_ASSEMBLY_AVAILABLE:
        st.error("❌ sequence_assembly module not loaded.")
        return

    eligible_records = [r for r in agent.generation_history if r.status == "succeeded" and r.output_url]

    gen_shots = st.session_state.get("mmh3_shots", [])
    if "mmh3_sequence_shots" not in st.session_state:
        st.session_state["mmh3_sequence_shots"] = []
    if "mmh3_sequence_uploaded_takes" not in st.session_state:
        st.session_state["mmh3_sequence_uploaded_takes"] = {}  # task_id -> SelectedTake
    seq_shots = st.session_state["mmh3_sequence_shots"]
    uploaded_takes = st.session_state["mmh3_sequence_uploaded_takes"]

    # Sync by each generation-shot's stable id, never by its label text --
    # labels are free-text and not unique, so two shots sharing a label
    # (e.g. mid-rename) must NOT collapse into one Sequence Assembly slot.
    # Renaming a shot updates its existing slot's displayed label in place
    # instead of creating a stale duplicate.
    existing_by_gen_id = {s["gen_shot_id"]: s for s in seq_shots if s.get("gen_shot_id")}
    for i, s in enumerate(gen_shots):
        label = s["label"] or f"Shot {i + 1:02d}"
        existing = existing_by_gen_id.get(s["id"])
        if existing is not None:
            existing["shot_label"] = label
        else:
            new_entry = {
                "id": str(uuid.uuid4()), "gen_shot_id": s["id"], "shot_label": label,
                "task_id": None, "in": 0.0, "out": None,
            }
            seq_shots.append(new_entry)
            existing_by_gen_id[s["id"]] = new_entry

    if not seq_shots:
        st.info("Add shots above first, then come back here to assemble them.")
        return

    # Unify both sources into one SelectedTake-keyed lookup, so the rest of
    # this function doesn't need to care where a take came from.
    takes_by_id: Dict[str, "SelectedTake"] = dict(uploaded_takes)
    record_by_id = {r.task_id: r for r in eligible_records}
    for r in eligible_records:
        takes_by_id[r.task_id] = _selected_take_from_generation_record(r)

    sequence_title = st.text_input("Sequence title", value="Sequence", key="mmh3_seq_title")

    for i, seq_shot in enumerate(seq_shots):
        sid = seq_shot.get("id") or str(i)
        st.markdown(f"**{seq_shot['shot_label']}**")

        source_choice = st.radio(
            "Take source", ["From generation history", "Upload local file"],
            key=f"mmh3_seq_source_{sid}", horizontal=True,
        )

        if source_choice == "From generation history":
            matching = [t for t in takes_by_id.values() if t.provider != "local_upload" and t.shot_label_hint == seq_shot["shot_label"]]
            other = [t for t in takes_by_id.values() if t.provider != "local_upload" and t.shot_label_hint != seq_shot["shot_label"]]
            ordered = matching + other

            def _fmt(t):
                mismatch = " ⚠️ (different shot)" if t.shot_label_hint != seq_shot["shot_label"] else ""
                label = t.shot_label_hint or "(unlabeled)"
                return f"{label} · {t.task_id} · {t.duration_seconds:.1f}s{mismatch}"

            if not ordered:
                st.info("No succeeded generations in this session yet.")
            else:
                options = ["(none selected)"] + [_fmt(t) for t in ordered]
                current_idx = 0
                if seq_shot.get("task_id"):
                    for j, t in enumerate(ordered):
                        if t.task_id == seq_shot["task_id"]:
                            current_idx = j + 1
                            break
                choice = st.selectbox("Selected take", options, index=current_idx, key=f"mmh3_seq_take_{sid}")
                seq_shot["task_id"] = None if choice == "(none selected)" else ordered[options.index(choice) - 1].task_id
        else:
            # No `type=` filter here deliberately: Streamlit maps it to the
            # browser's native file-picker `accept` filter, and on macOS
            # (Safari in particular) that filter can grey out or reject
            # genuinely valid .mp4/.mov files due to browser-side MIME
            # sniffing quirks, independent of the actual extension. We
            # accept anything and validate the extension ourselves instead.
            uploaded_file = st.file_uploader(
                f"Upload video for {seq_shot['shot_label']}", key=f"mmh3_seq_local_upload_{sid}",
                help="Accepts .mp4/.mov. Recovers a previously-generated clip whose in-app record was lost to a session/redeploy reset.",
            )
            if uploaded_file is not None and not uploaded_file.name.lower().endswith((".mp4", ".mov")):
                st.error(f"❌ Unsupported file type: {uploaded_file.name} — please upload an .mp4 or .mov file.")
            elif uploaded_file is not None:
                already = seq_shot.get("_uploaded_name") == uploaded_file.name
                if not already:
                    take = register_local_file(uploaded_file.getvalue())
                    uploaded_takes[take.task_id] = take
                    takes_by_id[take.task_id] = take
                    seq_shot["task_id"] = take.task_id
                    seq_shot["_uploaded_name"] = uploaded_file.name
                st.caption(f"✅ Registered as a local take ({takes_by_id[seq_shot['task_id']].duration_seconds:.1f}s).")

        if seq_shot.get("task_id"):
            take = takes_by_id.get(seq_shot["task_id"])
            if take:
                col1, col2 = st.columns(2)
                with col1:
                    seq_shot["in"] = st.number_input(
                        "In (s)", min_value=0.0, max_value=float(take.duration_seconds),
                        value=float(seq_shot.get("in") or 0.0), step=0.1, key=f"mmh3_seq_in_{sid}",
                    )
                with col2:
                    default_out = seq_shot.get("out")
                    if default_out is None:
                        default_out = float(take.duration_seconds)
                    seq_shot["out"] = st.number_input(
                        "Out (s)", min_value=0.0, max_value=float(take.duration_seconds),
                        value=float(default_out), step=0.1, key=f"mmh3_seq_out_{sid}",
                    )
                if st.button(f"▶️ Preview {seq_shot['shot_label']}", key=f"mmh3_seq_preview_one_{sid}"):
                    preview_source = take.source_url or take.cached_path
                    if preview_source:
                        st.video(preview_source)
        st.markdown("---")

    def _build_sequence():
        shots = []
        for seq_shot in seq_shots:
            if not seq_shot.get("task_id"):
                return None, seq_shot["shot_label"]
            take = takes_by_id.get(seq_shot["task_id"])
            if not take:
                return None, seq_shot["shot_label"]
            shots.append(SequenceShot(
                shot_label=seq_shot["shot_label"], take=take,
                in_seconds=seq_shot.get("in") or 0.0, out_seconds=seq_shot.get("out"),
            ))
        return Sequence(title=sequence_title, shots=shots), None

    sequence, missing_label = _build_sequence()
    if sequence is None:
        st.warning(f"⚠️ Select a take for '{missing_label}' before previewing or exporting.")
        return

    st.markdown(f"**Estimated duration: {sequence.estimated_duration():.1f} s**")
    for s in sequence.shots:
        st.caption(f"- {s.shot_label}: {s.trimmed_duration():.1f}s")

    colp, cole = st.columns(2)
    with colp:
        preview_clicked = st.button("▶️ Preview Sequence", key="mmh3_seq_preview_all")
    with cole:
        export_clicked = st.button("🎬 Export Movie (MP4)", type="primary", key="mmh3_seq_export")

    if preview_clicked or export_clicked:
        with st.spinner("Assembling sequence..."):
            output_path = Path(tempfile.gettempdir()) / f"sequence_{uuid.uuid4().hex}.mp4"
            try:
                assemble_sequence(sequence, output_path)
            except MaterializationError as e:
                st.error(f"❌ Could not use the take selected for shot '{e.shot_label}' (task {e.task_id}): {e.reason}")
                return
            except SequenceAssemblyError as e:
                st.error(f"❌ Assembly failed: {e}")
                return

        st.video(str(output_path))
        if export_clicked:
            st.download_button(
                "⬇️ Download MP4",
                data=output_path.read_bytes(),
                file_name=f"{(sequence_title or 'sequence').replace(' ', '_')}.mp4",
                mime="video/mp4",
                key="mmh3_seq_download",
            )
