#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎥 Runway Video Generation UI Component
For AI Studio Elsewhere - AI Film Director Interface

Integrates with runway_video_agent.py
"""

import streamlit as st
import subprocess
import os
import tempfile
from pathlib import Path
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

try:
    from runway_video_agent import (
        RunwayVideoAgent, VideoGenRequest, VideoGenResult,
        get_runway_agent
    )
    RUNWAY_AVAILABLE = True
except ImportError:
    RUNWAY_AVAILABLE = False
    logger.warning("⚠️ Runway Video Agent not available")

# ============================================================
# DIRECTOR PROMPT ENGINE
# ============================================================

_DIRECTOR_STYLES = {
    "Cinematic": {
        "base": "Cinematic film. Shallow depth of field. Film grain. Professional lighting.",
        "motion": "Slow deliberate camera movement. Gradual environmental shifts.",
    },
    "Dynamic": {
        "base": "Kinetic film aesthetic. High contrast. Physical tension.",
        "motion": "Handheld urgency. Quick angle shifts. Reactive camera.",
    },
    "Experimental": {
        "base": "Arthouse cinema. Unconventional framing. Poetic visual logic.",
        "motion": "Time dilation. Abstract motion. Fragmented perception.",
    },
    "Noir": {
        "base": "Black and white. 1940s film noir. High contrast shadows. Volumetric light.",
        "motion": "Slow dolly. Dust particles. Light flickering. Shadow movement.",
    },
}

_SHOT_CAMERAS = {
    "wide":   "Slow dolly forward from wide establishing shot. Architectural stillness.",
    "push":   "Gradual push-in toward focal point. Subtle handheld vibration.",
    "detail": "Static close-up of environmental detail. Light changing across surface.",
    "close":  "Slow rack focus to face or object. Breathing depth-of-field shift.",
}

_CLASSIFICATION_CAMERA = {
    "ATMOSPHERIC": "slow dolly forward, dust particles in air, light flickering, environmental breath",
    "ACTION":      "handheld movement, quick push-in, dynamic angle shift, wind and debris",
    "EMOTIONAL":   "slow close-up, shallow depth of field, soft focus, barely perceptible breathing motion",
    "DIALOGUE":    "subtle push-in on face, slight handheld sway, rack focus between subjects",
    "EXPOSITION":  "slow wide pan, architectural framing, deliberate spatial reveal",
    "TRANSITION":  "slow pull-back, ambient drift, temporal softness",
}


def generate_shot_sequence(scene: Dict) -> List[Dict]:
    """Generate 4-shot director sequence from scene data."""
    classification = scene.get("classification", "ATMOSPHERIC")
    heading = scene.get("heading", "Scene")

    shots = [
        {"type": "wide",   "label": "Establishing",
         "description": f"Wide establishing shot — {heading}"},
        {"type": "push",   "label": "Movement",
         "description": f"Push toward focal point — {heading}"},
        {"type": "detail", "label": "Atmosphere",
         "description": f"Environmental detail — light, texture, space"},
        {"type": "close",  "label": "Tension",
         "description": f"Close — final frame holds in still tension"},
    ]

    # Add camera from classification
    camera_base = _CLASSIFICATION_CAMERA.get(classification, _CLASSIFICATION_CAMERA["ATMOSPHERIC"])
    for shot in shots:
        shot["camera"] = _SHOT_CAMERAS[shot["type"]]
        shot["classification_camera"] = camera_base

    return shots


def build_cinematic_video_prompt(scene: Dict, shot: Dict, director_style: str = "Cinematic") -> str:
    """Build director-language video prompt from scene + shot type + style."""
    style_cfg = _DIRECTOR_STYLES.get(director_style, _DIRECTOR_STYLES["Cinematic"])
    heading    = scene.get("heading", "Scene")
    action     = scene.get("prompt", "")[:200]
    camera     = shot.get("camera", _SHOT_CAMERAS["wide"])
    motion_env = (
        "Doors moving in wind. Shadows shifting across surfaces. "
        "Fabric or objects reacting to environment. Subtle presence implied."
    )
    shot_sequence = (
        "Shot sequence: "
        "1. Wide establishing. "
        "2. Slow push toward doorway or focal point. "
        "3. Light entering through opening. "
        "4. Final frame holds in still tension."
    )

    return (
        f"{style_cfg['base']}\n\n"
        f"Scene: {heading}\n\n"
        f"Description: {action}\n\n"
        f"Camera: {camera}\n\n"
        f"Motion: {style_cfg['motion']} {motion_env}\n\n"
        f"{shot_sequence}"
    )


# ============================================================
# FFMPEG PIPELINE
# ============================================================

COLOR_GRADES = {
    "None":          None,
    "Cinematic Warm": "eq=saturation=1.1:gamma_r=1.08:gamma_b=0.94",
    "Noir B&W":      "hue=s=0,eq=contrast=1.35:brightness=-0.05",
    "Dream Blue":    "eq=saturation=0.8:gamma_b=1.12:gamma_r=0.95",
    "Vintage Film":  "curves=vintage",
}


def _ffmpeg_available() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def stitch_videos(video_paths: List[str], output_path: str) -> Optional[str]:
    """Concatenate video files with ffmpeg. Returns output path or None."""
    if not _ffmpeg_available():
        return None
    valid = [p for p in video_paths if Path(p).exists()]
    if not valid:
        return None
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for p in valid:
            f.write(f"file '{p}'\n")
        concat_file = f.name
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", concat_file, "-c", "copy", output_path],
            capture_output=True, timeout=120
        )
        os.unlink(concat_file)
        return output_path if Path(output_path).exists() else None
    except Exception:
        return None


def apply_color_grade(video_path: str, grade_filter: str, output_path: str) -> Optional[str]:
    """Apply ffmpeg color grade filter. Returns output path or None."""
    if not _ffmpeg_available() or not Path(video_path).exists():
        return None
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", video_path,
             "-vf", grade_filter, "-c:a", "copy", output_path],
            capture_output=True, timeout=120
        )
        return output_path if Path(output_path).exists() else None
    except Exception:
        return None


# ============================================================
# TIMELINE BAR
# ============================================================

def _timeline_bar(shots: List[Dict], generated: Dict) -> str:
    """ASCII timeline bar — filled if clip exists, empty if not."""
    bar = ""
    for shot in shots:
        stype = shot["type"]
        filled = stype in generated and generated[stype]
        bar += ("█" if filled else "░") * 4 + " "
    return bar.strip()


# ============================================================
# MAIN UI
# ============================================================

def display_video_generation_tab(scenes: List[Dict], project_title: str):
    """Main video generation interface — Director Mode first."""

    if not RUNWAY_AVAILABLE:
        st.error("❌ Runway Video Agent not loaded — check runway_video_agent.py")
        return

    st.header("🎬 AI Film Director")

    if not scenes:
        st.warning("⚠️ No scenes available. Extract scenes first.")
        return

    agent = get_runway_agent()

    if not agent.available:
        st.warning("⚠️ Runway API not configured. Add RUNWAY_API_KEY to Railway environment.")
        return

    tab_director, tab_single, tab_batch = st.tabs([
        "🎬 Director Mode",
        "🎥 Single Shot",
        "📹 Batch",
    ])

    # ── Director Mode ─────────────────────────────────────────

    with tab_director:
        st.subheader("🎬 Director Mode — Multi-Shot Scene Pipeline")

        col1, col2 = st.columns([2, 1])
        with col1:
            scene_options = {f"Scene {i+1}: {s.get('heading','Untitled')}": i for i, s in enumerate(scenes)}
            selected_label = st.selectbox("Select Scene", list(scene_options.keys()), key="dir_scene")
            scene = scenes[scene_options[selected_label]]
        with col2:
            director_style = st.selectbox("Director Style", list(_DIRECTOR_STYLES.keys()), key="dir_style")

        concept_path = scene.get("concept_image_path")
        if concept_path and Path(concept_path).exists():
            st.image(concept_path, width=600, caption="Reference frame")

        shots = generate_shot_sequence(scene)

        st.markdown("#### Shot Sequence")
        cols = st.columns(4)
        for i, shot in enumerate(shots):
            with cols[i]:
                st.markdown(f"**{shot['label']}**")
                st.caption(shot["type"].upper())

        with st.expander("Shot Control Panel"):
            for shot in shots:
                st.markdown(f"**{shot['label']} — {shot['type'].upper()}**")
                c1, c2 = st.columns(2)
                with c1:
                    shot["camera"] = st.selectbox(
                        "Camera",
                        ["Slow dolly forward", "Push-in", "Static", "Handheld", "Pull-back", "Orbit"],
                        key=f"cam_{shot['type']}",
                    )
                with c2:
                    shot["lighting"] = st.selectbox(
                        "Lighting",
                        ["Natural", "Dramatic", "Low-key", "High contrast", "Soft diffuse"],
                        key=f"lit_{shot['type']}",
                    )
                st.divider()

        with st.expander("Preview Prompts"):
            for shot in shots:
                st.markdown(f"**{shot['label']}**")
                prompt = build_cinematic_video_prompt(scene, shot, director_style)
                st.text_area("", prompt, height=120, key=f"prompt_prev_{shot['type']}", disabled=True)

        clips_key = f"dir_clips_{scene.get('id','scene')}"
        if clips_key not in st.session_state:
            st.session_state[clips_key] = {}
        generated = st.session_state[clips_key]

        st.markdown("#### Timeline")
        st.markdown(f"`{_timeline_bar(shots, generated)}`")
        st.caption("  ".join(f"`{s['label'][:4]}`" for s in shots))

        if st.button("🎬 Generate Shot Sequence", type="primary", use_container_width=True, key="dir_gen"):
            concept_image = scene.get("concept_image")
            if not concept_image:
                st.error("❌ Generate concept art first — Runway requires a reference image.")
            else:
                progress = st.progress(0, text="Starting shot sequence...")
                for idx, shot in enumerate(shots):
                    progress.progress(idx / len(shots), text=f"Generating {shot['label']} shot...")
                    prompt = build_cinematic_video_prompt(scene, shot, director_style)
                    request = VideoGenRequest(
                        scene_id=f"{scene.get('id','scene')}_{shot['type']}",
                        scene_heading=f"{scene.get('heading','')} — {shot['label']}",
                        prompt_en=prompt,
                        motion_type=None,
                        style=director_style.lower(),
                        duration=5,
                        prompt_image=concept_image,
                        notes=f"{project_title} / Director Mode",
                    )
                    result = agent.generate_video(request)
                    if result.video_url:
                        generated[shot["type"]] = result.video_url
                        st.session_state[clips_key] = generated
                progress.progress(1.0, text="All shots generated.")
                st.success(f"✅ {len(generated)} shots generated")
                st.rerun()

        if generated:
            st.markdown("#### Generated Clips")
            clip_cols = st.columns(min(len(generated), 4))
            video_paths = []
            for i, shot in enumerate(shots):
                stype = shot["type"]
                if stype not in generated:
                    continue
                url = generated[stype]
                with clip_cols[i % 4]:
                    st.caption(shot["label"])
                    if Path(url).exists():
                        st.video(url)
                        video_paths.append(url)
                    else:
                        st.info(f"📹 {url[:60]}…")

            st.markdown(f"`{_timeline_bar(shots, generated)}`")

            st.markdown("#### Color Grade")
            c1, c2 = st.columns([2, 1])
            with c1:
                grade_choice = st.selectbox("Grade", list(COLOR_GRADES.keys()), key="dir_grade")
            with c2:
                apply_grade = st.button("🎨 Apply Grade", key="dir_apply_grade")

            if apply_grade and grade_choice != "None":
                if not _ffmpeg_available():
                    st.warning("⚠️ ffmpeg not installed")
                elif not video_paths:
                    st.warning("⚠️ No local video files to grade")
                else:
                    grade_filter = COLOR_GRADES[grade_choice]
                    graded = []
                    for vp in video_paths:
                        out = vp.replace(".mp4", "_graded.mp4")
                        result = apply_color_grade(vp, grade_filter, out)
                        if result:
                            graded.append(result)
                    if graded:
                        st.success(f"✅ Graded {len(graded)} clips")

            if st.button("🎞 Stitch Clips → Scene Video", use_container_width=True, key="dir_stitch"):
                if not _ffmpeg_available():
                    st.warning("⚠️ ffmpeg not installed — `brew install ffmpeg`")
                elif not video_paths:
                    st.warning("⚠️ Clips are streaming URLs — download them first to assemble locally.")
                else:
                    output = str(Path(video_paths[0]).parent / f"scene_{scene.get('id','assembled')}.mp4")
                    final = stitch_videos(video_paths, output)
                    if final:
                        st.success("✅ Scene assembled")
                        st.video(final)
                        with open(final, "rb") as f:
                            st.download_button(
                                "⬇ Download Scene Video",
                                data=f.read(),
                                file_name=f"{scene.get('id','scene')}_assembled.mp4",
                                mime="video/mp4",
                            )
                    else:
                        st.error("❌ Assembly failed")

    # ── Single Shot ───────────────────────────────────────────

    with tab_single:
        st.subheader("🎥 Single Shot Generation")

        col1, col2 = st.columns(2)
        with col1:
            scene_options = {f"Scene {i+1}: {s.get('heading','Untitled')}": i for i, s in enumerate(scenes)}
            selected_label = st.selectbox("Select Scene", list(scene_options.keys()), key="single_scene")
            scene = scenes[scene_options[selected_label]]
        with col2:
            motion_options = agent.get_motion_options()
            selected_motion = st.selectbox(
                "Camera Motion", list(motion_options.keys()),
                format_func=lambda x: f"{x.replace('_',' ').title()} — {motion_options[x]}",
                key="single_motion",
            )

        col1, col2 = st.columns(2)
        with col1:
            style_options = agent.get_style_options()
            selected_style = st.selectbox("Visual Style", list(style_options.keys()), key="single_style")
        with col2:
            duration = st.slider("Duration (seconds)", 2, 10, 5, step=1, key="single_dur")

        director_style_single = st.selectbox("Director Style", list(_DIRECTOR_STYLES.keys()), key="single_dir_style")
        shot_type_single = st.selectbox("Shot Type", ["wide", "push", "detail", "close"], key="single_shot_type")
        shot_dummy = {"type": shot_type_single, "camera": _SHOT_CAMERAS[shot_type_single]}
        prompt = build_cinematic_video_prompt(scene, shot_dummy, director_style_single)
        st.text_area("Cinematic Prompt", prompt, height=180, disabled=True, key="single_prompt_preview")

        concept_image = scene.get("concept_image")
        concept_image_path = scene.get("concept_image_path")
        if concept_image:
            try:
                if concept_image_path and Path(concept_image_path).exists():
                    st.image(concept_image_path, width=400, caption="Reference image")
                elif concept_image.startswith("data:"):
                    import base64 as _b64
                    img_bytes = _b64.b64decode(concept_image.split(",", 1)[1])
                    st.image(img_bytes, width=400)
                else:
                    import requests as _req
                    st.image(_req.get(concept_image, timeout=10).content, width=400)
            except Exception:
                st.info("Concept image ready")
        else:
            st.warning("⚠️ No concept image. Generate concept art first.")

        if st.button("🎥 Generate Video", type="primary", use_container_width=True, key="single_gen"):
            if not concept_image:
                st.error("❌ Runway requires a reference image.")
            else:
                with st.spinner("⏳ Generating video…"):
                    request = VideoGenRequest(
                        scene_id=scene.get("id", "scene"),
                        scene_heading=scene.get("heading", "Scene"),
                        prompt_en=prompt,
                        motion_type=selected_motion,
                        style=selected_style,
                        duration=duration,
                        prompt_image=concept_image,
                        notes=f"Generated for {project_title}",
                    )
                    result = agent.generate_video(request)
                st.success(f"✅ {result.scene_id}")
                col1, col2, col3 = st.columns(3)
                col1.metric("Status", result.status)
                col2.metric("Motion", selected_motion.replace("_", " ").title())
                col3.metric("Duration", f"{result.duration}s")
                if result.video_url:
                    if Path(result.video_url).exists():
                        st.video(result.video_url)
                    else:
                        st.info(f"📹 {result.video_url}")

    # ── Batch ─────────────────────────────────────────────────

    with tab_batch:
        st.subheader("📹 Batch Generation")

        col1, col2 = st.columns(2)
        with col1:
            motion_options = agent.get_motion_options()
            selected_motions = st.multiselect(
                "Motion types", list(motion_options.keys()),
                default=list(motion_options.keys())[:3],
                format_func=lambda x: x.replace("_", " ").title(),
                key="batch_motions",
            )
        with col2:
            style_options = agent.get_style_options()
            selected_style = st.selectbox("Style", list(style_options.keys()), key="batch_style")

        scene_selection = st.multiselect(
            "Scenes",
            [f"Scene {i+1}: {s.get('heading','Untitled')}" for i, s in enumerate(scenes)],
            default=[f"Scene 1: {scenes[0].get('heading','Untitled')}"],
            key="batch_scenes",
        )
        selected_indices = [int(s.split(":")[0].replace("Scene ", "")) - 1 for s in scene_selection]

        if st.button("📹 Generate Batch", type="primary", use_container_width=True, key="batch_gen"):
            if not selected_motions:
                st.warning("Select at least one motion type")
            else:
                with st.spinner(f"⏳ Generating {len(selected_indices)} scenes…"):
                    results = agent.generate_videos_for_scenes(
                        [scenes[i] for i in selected_indices],
                        motion_types=selected_motions,
                        style=selected_style,
                    )
                st.success(f"✅ {len(results)} videos queued")
                st.dataframe(
                    [{"Scene": r.scene_id, "Status": r.status, "Duration": f"{r.duration}s"} for r in results],
                    use_container_width=True,
                )

    # ── History ───────────────────────────────────────────────

    st.markdown("---")
    history = agent.get_generation_history()
    if history:
        st.subheader("📊 History")
        st.dataframe(
            [{"Scene": h["scene_id"], "Prompt": h["prompt_used"][:50] + "…",
              "Motion": h.get("motion_applied") or "—", "Status": h["status"]} for h in history[-10:]],
            use_container_width=True,
        )

    status = agent.get_status()
    c1, c2, c3 = st.columns(3)
    c1.metric("Videos Generated", status["videos_generated"])
    c2.metric("Motion Types", len(status["motion_options"]))
    c3.metric("Style Presets", len(status["style_options"]))
