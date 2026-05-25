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


def _safe_path_exists(p: str) -> bool:
    """Path.exists() that never raises — guards against data URIs / long strings."""
    try:
        return Path(p).exists()
    except OSError:
        return False


# Resolve ffmpeg binary — imageio-ffmpeg ships its own, bypassing Nix PATH issues
def _get_ffmpeg_bin() -> Optional[str]:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    import shutil
    return shutil.which("ffmpeg")

_FFMPEG_BIN = _get_ffmpeg_bin()

try:
    from runway_video_agent import (
        RunwayVideoAgent, VideoGenRequest, VideoGenResult,
        get_runway_agent
    )
    RUNWAY_AVAILABLE = True
except ImportError:
    RUNWAY_AVAILABLE = False
    logger.warning("⚠️ Runway Video Agent not available")

try:
    from audio_agent import generate_ambient_sound as _gen_audio, get_status as _audio_status
    AUDIO_AVAILABLE = _audio_status()["available"]
except ImportError:
    AUDIO_AVAILABLE = False
    def _gen_audio(*a, **kw): return None

try:
    from narration_agent import (
        generate_narration as _generate_narration,
        get_status as _narration_status,
        LANGUAGES as _NARRATION_LANGUAGES,
    )
    NARRATION_AVAILABLE = _narration_status()["available"]
except ImportError:
    NARRATION_AVAILABLE = False
    _NARRATION_LANGUAGES = {}
    def _generate_narration(*a, **kw): return {"text": None, "audio_path": None, "error": "not loaded"}

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
        subprocess.run([_FFMPEG_BIN, "-version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def _download_clip(url: str, scene_id: str, shot_type: str) -> Optional[str]:
    """Download a Runway streaming URL to a local temp file. Returns local path or None."""
    try:
        import uuid, requests as _req
        safe_id = str(scene_id)[:12].replace(" ", "_").replace("/", "_")
        dest = Path(tempfile.gettempdir()) / f"clip_{safe_id}_{shot_type}_{uuid.uuid4().hex[:6]}.mp4"
        resp = _req.get(url, timeout=120, stream=True)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                f.write(chunk)
        return str(dest)
    except Exception as e:
        logger.warning(f"⚠️ Could not download clip {url}: {e}")
        return None


def stitch_videos(video_paths: List[str], output_path: str) -> Optional[str]:
    """Concatenate video files with ffmpeg. Returns output path or None."""
    if not _ffmpeg_available():
        return None
    valid = [p for p in video_paths if _safe_path_exists(p)]
    if not valid:
        return None
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for p in valid:
            f.write(f"file '{p}'\n")
        concat_file = f.name
    try:
        result = subprocess.run(
            [_FFMPEG_BIN, "-y", "-f", "concat", "-safe", "0",
             "-i", concat_file, "-c", "copy", output_path],
            capture_output=True, timeout=120
        )
        os.unlink(concat_file)
        return output_path if _safe_path_exists(output_path) else None
    except Exception:
        return None


def apply_color_grade(video_path: str, grade_filter: str, output_path: str) -> Optional[str]:
    """Apply ffmpeg color grade filter. Returns output path or None."""
    if not _ffmpeg_available() or not _safe_path_exists(video_path):
        return None
    try:
        result = subprocess.run(
            [_FFMPEG_BIN, "-y", "-i", video_path,
             "-vf", grade_filter, "-c:a", "copy", output_path],
            capture_output=True, timeout=120
        )
        return output_path if _safe_path_exists(output_path) else None
    except Exception:
        return None


def merge_audio_video(video_path: str, audio_path: str, output_path: str) -> Optional[str]:
    """Mix audio track into video with ffmpeg. Returns output path or None."""
    if not _ffmpeg_available() or not _safe_path_exists(video_path) or not _safe_path_exists(audio_path):
        return None
    try:
        subprocess.run(
            [_FFMPEG_BIN, "-y", "-i", video_path, "-i", audio_path,
             "-c:v", "copy", "-c:a", "aac",
             "-map", "0:v:0", "-map", "1:a:0",
             "-shortest", output_path],
            capture_output=True, timeout=120,
        )
        return output_path if _safe_path_exists(output_path) else None
    except Exception:
        return None


def _process_uploaded_photo(image_bytes: bytes) -> Optional[str]:
    """Decode uploaded photo → center-crop 1280×720 → film effects → base64 data URI."""
    try:
        import io, base64
        from PIL import Image, ImageFilter, ImageEnhance
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        tw, th = 1280, 720
        ratio = max(tw / img.width, th / img.height)
        nw, nh = int(img.width * ratio), int(img.height * ratio)
        img = img.resize((nw, nh), Image.LANCZOS)
        left = (nw - tw) // 2
        top  = (nh - th) // 2
        img  = img.crop((left, top, left + tw, top + th))
        img  = img.filter(ImageFilter.GaussianBlur(radius=0.3))
        img  = ImageEnhance.Contrast(img).enhance(1.1)
        img  = ImageEnhance.Color(img).enhance(0.95)
        buf  = io.BytesIO()
        img.save(buf, format="PNG")
        b64  = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        logger.error(f"Photo processing failed: {e}")
        return None


def mix_audio_tracks(primary: str, background: str, output_path: str, bg_volume: float = 0.3) -> Optional[str]:
    """ffmpeg amix: primary at full volume, background at bg_volume. Returns path or None."""
    if not _ffmpeg_available() or not _safe_path_exists(primary) or not _safe_path_exists(background):
        return None
    try:
        subprocess.run(
            [_FFMPEG_BIN, "-y", "-i", primary, "-i", background,
             "-filter_complex", f"amix=inputs=2:duration=first:weights=1 {bg_volume}",
             output_path],
            capture_output=True, timeout=60,
        )
        return output_path if _safe_path_exists(output_path) else None
    except Exception:
        return None


# ── Cultural sound profiles ───────────────────────────────────

_SOUND_PROFILES = {
    "Chinese": "wind, distant temple bell, minimal guzheng resonance, ancient stone atmosphere",
    "French":  "soft urban air, distant footsteps on stone, minimal piano, café ambience",
    "Thai":    "humid tropical air, insects, distant water, soft traditional wind tones",
    "Global":  "natural atmospheric environment, cinematic minimal score, subtle presence",
}

def _detect_sound_profile(scene: Dict) -> str:
    desc = (scene.get("prompt", "") + " " + scene.get("heading", "")).lower()
    if any(w in desc for w in ["temple", "china", "chinese", "beijing", "shanghai", "guzheng", "dynasty"]):
        return "Chinese"
    if any(w in desc for w in ["paris", "french", "france", "café", "cafe", "boulangerie", "montmartre"]):
        return "French"
    if any(w in desc for w in ["tropical", "thailand", "thai", "jungle", "humid", "mangrove", "monsoon"]):
        return "Thai"
    return "Global"


# ── Cinematic style presets (Photo → Clip) ───────────────────

_CINEMATIC_STYLE_MAP = {
    "Natural Realism": "photorealistic, natural light, subtle motion, environmental breath",
    "Noir":            "black and white, high contrast, deep shadows, moody atmosphere",
    "Dreamlike":       "soft ethereal light, gentle diffusion, floating atmosphere, pastel depth",
    "Gritty":          "film grain, harsh directional light, raw texture, documentary realism",
}

def _enhance_photo_prompt(style: str) -> str:
    style_layer = _CINEMATIC_STYLE_MAP.get(style, "")
    return (
        f"Cinematic film. Slow push-in camera movement. "
        f"Shallow depth of field. Subtle environmental motion. "
        f"Realistic lighting shift. Depth and atmosphere. {style_layer}."
    )

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
    import traceback as _tb2

    # Sanitize: remove any data URI from fields other than concept_image
    for _s in scenes:
        for _k, _v in list(_s.items()):
            if _k != "concept_image" and isinstance(_v, str) and len(_v) > 260:
                _s[_k] = None

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

    tab_director, tab_single, tab_batch, tab_photo = st.tabs([
        "🎬 Director Mode",
        "🎥 Single Shot",
        "📹 Batch",
        "✨ Bring Image to Life",
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
        if concept_path:
            try:
                if concept_path.startswith("data:image/"):
                    import base64 as _b64disp
                    st.image(_b64disp.b64decode(concept_path.split(",", 1)[1]), width=600, caption="Reference frame")
                elif _safe_path_exists(concept_path):
                    st.image(concept_path, width=600, caption="Reference frame")
            except Exception:
                pass

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
        # Drop any stale data-URI entries from session state
        generated = {k: v for k, v in generated.items()
                     if isinstance(v, str) and not v.startswith("data:") and len(v) <= 260}
        st.session_state[clips_key] = generated

        st.markdown("#### Timeline")
        st.markdown(f"`{_timeline_bar(shots, generated)}`")
        st.caption("  ".join(f"`{s['label'][:4]}`" for s in shots))

        if st.button("🎬 Generate Shot Sequence", type="primary", use_container_width=True, key="dir_gen"):
            concept_image = scene.get("concept_image")
            if not concept_image:
                st.error("❌ Generate concept art first — Runway requires a reference image.")
            else:
                progress = st.progress(0, text="Starting shot sequence...")
                shot_errors = []
                try:
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
                            local = _download_clip(result.video_url, scene.get("id","scene"), shot["type"])
                            generated[shot["type"]] = local or result.video_url
                            st.session_state[clips_key] = generated
                            progress.progress((idx + 1) / len(shots), text=f"✅ {shot['label']} done")
                        else:
                            err = (result.metadata or {}).get("error") or f"status={result.status}"
                            shot_errors.append(f"**{shot['label']}** ({shot['type']}): {err}")
                            progress.progress((idx + 1) / len(shots), text=f"❌ {shot['label']} failed")
                except Exception as exc:
                    shot_errors.append(f"**Unexpected error**: {type(exc).__name__}: {exc}")

                progress.progress(1.0, text="Done.")
                if shot_errors:
                    st.error("Generation errors:\n\n" + "\n\n".join(shot_errors))
                if generated:
                    st.success(f"✅ {len(generated)}/{len(shots)} shots generated")
                    st.rerun()

        if generated:
            st.markdown("#### Generated Clips")
            clip_cols = st.columns(min(len(generated), 4))
            video_paths = []
            for i, shot in enumerate(shots):
                stype = shot["type"]
                if stype not in generated:
                    continue
                ref = generated[stype]
                with clip_cols[i % 4]:
                    st.caption(shot["label"])
                    if _safe_path_exists(ref):
                        st.video(ref)
                        video_paths.append(ref)
                    else:
                        st.markdown(f"[📥 Download clip]({ref})")
                        st.caption("URL — not yet stitchable")

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

            st.markdown("#### Ambient Audio")
            if not AUDIO_AVAILABLE:
                st.caption("Add ELEVENLABS_API_KEY to Railway to enable ambient sound generation.")
            else:
                _profile     = _detect_sound_profile(scene)
                _default_ap  = _SOUND_PROFILES.get(_profile, _SOUND_PROFILES["Global"])
                _a1, _a2 = st.columns([3, 1])
                with _a1:
                    audio_prompt = st.text_input(
                        f"Sound description  ·  *{_profile} profile auto-detected*",
                        value=_default_ap, key="dir_audio_prompt",
                    )
                with _a2:
                    audio_dur = st.slider("Duration (s)", 3, 22,
                                          min(22, max(3, len(video_paths) * 5)),
                                          key="dir_audio_dur")
                if st.button("🎵 Generate Ambient Sound", key="dir_gen_audio"):
                    with st.spinner("Generating ambient sound via ElevenLabs..."):
                        _ap = _gen_audio(audio_prompt, float(audio_dur))
                    if _ap:
                        st.session_state[f"audio_{clips_key}"] = _ap
                        st.audio(_ap)
                        st.success("✅ Ambient sound ready — stitch clips to merge")
                    else:
                        st.error("❌ Audio generation failed — check ELEVENLABS_API_KEY")
                elif st.session_state.get(f"audio_{clips_key}") and _safe_path_exists(st.session_state[f"audio_{clips_key}"]):
                    st.audio(st.session_state[f"audio_{clips_key}"])
                    st.caption("Ambient sound ready")

            st.markdown("#### Narration")
            if not NARRATION_AVAILABLE:
                st.caption("Narration uses OPENAI_API_KEY — already set for concept art.")
            else:
                _nar_key  = f"narration_{clips_key}"
                _nar_lang = st.selectbox(
                    "Language",
                    ["None"] + list(_NARRATION_LANGUAGES.keys()),
                    key="dir_nar_lang",
                )
                if _nar_lang != "None":
                    if st.button("🗣 Generate Narration", key="dir_gen_nar"):
                        with st.spinner(f"Generating {_nar_lang} narration via GPT + TTS..."):
                            _nr = _generate_narration(
                                scene.get("heading", ""),
                                scene.get("prompt", ""),
                                _nar_lang,
                            )
                        if _nr["audio_path"]:
                            st.session_state[_nar_key] = _nr
                            st.success(f"✅  *{_nr['text']}*")
                            st.audio(_nr["audio_path"])
                        else:
                            st.error(f"❌ {_nr.get('error', 'Failed')}")
                    elif st.session_state.get(_nar_key):
                        _nr_saved = st.session_state[_nar_key]
                        if _safe_path_exists(_nr_saved.get("audio_path", "")):
                            st.caption(f"*{_nr_saved['text']}*")
                            st.audio(_nr_saved["audio_path"])

            st.markdown("#### Export Mode")
            export_mode = st.radio(
                "Version",
                ["🎬 Festival (ambient only)", "🌍 Localized (narration + ambient)", "📺 Commercial (narration + strong ambient)"],
                horizontal=True,
                key="dir_export_mode",
            )

            if st.button("🎞 Stitch Clips → Scene Video", use_container_width=True, key="dir_stitch"):
                if not _ffmpeg_available():
                    st.warning("⚠️ ffmpeg not available on this server")
                elif not video_paths:
                    st.warning("⚠️ Clips are streaming URLs — download them first to assemble locally.")
                else:
                    output = str(Path(video_paths[0]).parent / f"scene_{scene.get('id','assembled')}.mp4")
                    final = stitch_videos(video_paths, output)
                    if final:
                        _saved_audio  = st.session_state.get(f"audio_{clips_key}")
                        _nar_data     = st.session_state.get(f"narration_{clips_key}")
                        _exp          = st.session_state.get("dir_export_mode", "🎬 Festival (ambient only)")
                        _nar_path     = None
                        _bg_vol       = 0.3

                        if "Localized" in _exp or "Commercial" in _exp:
                            if _nar_data and _safe_path_exists(_nar_data.get("audio_path", "")):
                                _nar_path = _nar_data["audio_path"]
                            if "Commercial" in _exp:
                                _bg_vol = 0.55

                        if _nar_path and _saved_audio and _safe_path_exists(_saved_audio):
                            _mixed_audio = str(Path(tempfile.gettempdir()) / f"mixed_{scene.get('id','x')}.mp3")
                            _mixed_audio = mix_audio_tracks(_nar_path, _saved_audio, _mixed_audio, _bg_vol)
                            if _mixed_audio:
                                _merged = merge_audio_video(final, _mixed_audio, final.replace(".mp4", "_narrated.mp4"))
                                if _merged:
                                    final = _merged
                                    st.success("✅ Narration + ambient mixed")
                        elif _nar_path:
                            _merged = merge_audio_video(final, _nar_path, final.replace(".mp4", "_narrated.mp4"))
                            if _merged:
                                final = _merged
                                st.success("✅ Narration merged")
                        elif _saved_audio and _safe_path_exists(_saved_audio):
                            _merged = merge_audio_video(final, _saved_audio, final.replace(".mp4", "_audio.mp4"))
                            if _merged:
                                final = _merged
                                st.success("✅ Ambient merged")

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
                if concept_image_path and not concept_image_path.startswith("data:") and _safe_path_exists(concept_image_path):
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
                if result.status == "failed":
                    err = result.metadata.get("error", "Unknown error") if result.metadata else "generation failed"
                    st.error(f"❌ Generation failed: {err}")
                else:
                    st.success(f"✅ {result.scene_id}")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Status", result.status)
                    col2.metric("Motion", selected_motion.replace("_", " ").title())
                    col3.metric("Duration", f"{result.duration}s")
                    if result.video_url:
                        local = _download_clip(result.video_url, scene.get("id","scene"), "single")
                        display_path = local or result.video_url
                        if local and _safe_path_exists(local):
                            st.video(local)
                        else:
                            st.markdown(f"[📥 Download video]({result.video_url})")
                with st.expander("🔍 Debug info", expanded=result.status == "failed"):
                    st.json({
                        "status": result.status,
                        "video_url": result.video_url or "(empty)",
                        "metadata": result.metadata or {},
                    })

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

    # ── Bring Image to Life ───────────────────────────────────

    with tab_photo:
        st.subheader("✨ Bring Image to Life")
        st.caption("Upload any photograph or still frame — the system applies cinematic motion.")

        uploaded = st.file_uploader(
            "Upload image",
            type=["png", "jpg", "jpeg", "webp"],
            key="photo_uploader",
            label_visibility="collapsed",
        )

        if uploaded:
            source_id = f"{uploaded.name}_{uploaded.size}"
            if st.session_state.get("photo_clip_source_id") != source_id:
                with st.spinner("Preparing frame..."):
                    uri = _process_uploaded_photo(uploaded.getvalue())
                if uri:
                    st.session_state["photo_clip_source_id"] = source_id
                    st.session_state["photo_clip_uri"] = uri
                    st.session_state.pop("photo_clip_result", None)
                else:
                    st.error("❌ Could not process image — try a different file.")

        clip_uri = st.session_state.get("photo_clip_uri")

        if clip_uri:
            import base64 as _b64ph
            img_bytes = _b64ph.b64decode(clip_uri.split(",", 1)[1])
            st.image(img_bytes, use_container_width=True)

            _ps1, _ps2 = st.columns([2, 1])
            with _ps1:
                photo_style = st.selectbox(
                    "Visual style",
                    list(_CINEMATIC_STYLE_MAP.keys()),
                    key="photo_style",
                )
            with _ps2:
                photo_dur = st.slider("Duration (s)", 2, 10, 5, key="photo_dur")

            _auto_prompt = _enhance_photo_prompt(photo_style)
            with st.expander("Advanced — view cinematic prompt"):
                st.code(_auto_prompt, language=None)

            if st.button("✨ Bring Image to Life", type="primary", use_container_width=True, key="photo_gen"):
                with st.spinner("Creating cinematic motion..."):
                    import uuid as _uuid_ph
                    req = VideoGenRequest(
                        scene_id=f"photo_{_uuid_ph.uuid4().hex[:6]}",
                        scene_heading="Bring Image to Life",
                        prompt_en=_auto_prompt,
                        motion_type=None,
                        style=photo_style.lower().replace(" ", "_"),
                        duration=photo_dur,
                        prompt_image=clip_uri,
                        notes=f"Bring Image to Life — {project_title}",
                    )
                    result = agent.generate_video(req)
                if result.video_url:
                    local = _download_clip(result.video_url, "photo", "clip")
                    st.session_state["photo_clip_result"] = local or result.video_url
                    st.rerun()
                else:
                    err = (result.metadata or {}).get("error", "generation failed")
                    st.error(f"❌ {err}")

            result_path = st.session_state.get("photo_clip_result")
            if result_path:
                if _safe_path_exists(result_path):
                    st.video(result_path)
                    with open(result_path, "rb") as _f:
                        st.download_button(
                            "⬇ Download",
                            data=_f.read(),
                            file_name="cinematic_clip.mp4",
                            mime="video/mp4",
                            key="photo_dl",
                        )
                else:
                    st.markdown(f"[📥 Download clip]({result_path})")

        elif not uploaded:
            st.info("Upload a photograph above to begin.")

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
