#!/usr/bin/env python3
"""
Cinematic Localization UI
Streamlit interface for the six-stage localization pipeline.
"""

import sys
import os
from pathlib import Path
from typing import List, Optional

import streamlit as st

# Ensure agents directory is on path
_AGENTS_DIR = Path(__file__).parent / "agents"
if str(_AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENTS_DIR))

try:
    from cinematic_localization_agent import (
        LocalizationMemory,
        LocalizationOrchestrator,
        LocalizationResult,
        SegmentationAgent,
        OutputAgent,
        SubtitleSegment,
        ANTHROPIC_AVAILABLE,
        OPENAI_AVAILABLE,
    )
    AGENT_AVAILABLE = True
except ImportError as e:
    AGENT_AVAILABLE = False
    _IMPORT_ERROR = str(e)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_memory_from_form(phrase_raw: str, voice_raw: str) -> LocalizationMemory:
    memory = LocalizationMemory()
    for line in phrase_raw.strip().split("\n"):
        line = line.strip()
        if "→" in line:
            src, tgt = line.split("→", 1)
            memory.phrase_lock[src.strip()] = tgt.strip()
        elif "->" in line:
            src, tgt = line.split("->", 1)
            memory.phrase_lock[src.strip()] = tgt.strip()
    for line in voice_raw.strip().split("\n"):
        line = line.strip()
        if ":" in line:
            name, desc = line.split(":", 1)
            memory.character_voice[name.strip()] = desc.strip()
    return memory


def _status_badge(status: str) -> str:
    colors = {"approved": "green", "revise": "red", "pending": "orange"}
    return f":{colors.get(status, 'gray')}[{status.upper()}]"


# ─────────────────────────────────────────────────────────────────────────────
# Main UI entry point
# ─────────────────────────────────────────────────────────────────────────────

def display_localization_ui():
    st.header("🌍 Cinematic Localization Engine")
    st.caption("Creative Direction → Agent Pipeline → Human Review  ·  AI proposes, director decides.")

    if not AGENT_AVAILABLE:
        st.error(f"Localization agent failed to import: {_IMPORT_ERROR}")
        return

    # LLM availability banner
    if not ANTHROPIC_AVAILABLE and not OPENAI_AVAILABLE:
        st.error("No LLM available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in your .env file.")
        return

    llm_label = "Claude (Anthropic)" if ANTHROPIC_AVAILABLE else "GPT-4o-mini (OpenAI)"
    st.success(f"LLM: {llm_label}")

    # ─── Pipeline Settings ───────────────────────────────────────────────────
    with st.expander("⚙️ Pipeline Settings", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            source_lang = st.selectbox(
                "Source Language",
                ["zh", "en", "fr", "ja", "ko", "it", "es"],
                index=0
            )
        with col2:
            target_lang = st.selectbox(
                "Target Language",
                ["DE", "EN", "FR", "JA", "ES", "IT", "PT", "KO", "ZH"],
                index=0
            )
        with col3:
            mode = st.selectbox(
                "Translation Mode",
                ["cinematic", "literal", "festival-safe", "edgy"],
                index=0,
                help=(
                    "cinematic: tone-aware, subtext preserved\n"
                    "literal: word-for-word accuracy\n"
                    "festival-safe: suitable for film festival submissions\n"
                    "edgy: raw, provocative — for specific scenes"
                )
            )

    # ─── Scene Context ───────────────────────────────────────────────────────
    with st.expander("🎬 Scene Context", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            scene_mood = st.text_input("Scene Mood", placeholder="intimate / confrontational / ironic")
        with col2:
            scene_character = st.text_input("Active Character", placeholder="Hong")
        with col3:
            scene_relationship = st.text_input("Relationship", placeholder="estranged lovers")

        scene_context = {
            "mood": scene_mood or "unspecified",
            "character": scene_character or "unspecified",
            "relationship": scene_relationship or "unspecified",
        }

    # ─── Memory / Consistency Rules ──────────────────────────────────────────
    with st.expander("🧠 Memory / Consistency Rules", expanded=False):
        st.caption("These rules persist across the entire batch — preventing tone drift.")
        col1, col2 = st.columns(2)
        with col1:
            phrase_lock_raw = st.text_area(
                "Phrase Locks  (source → target)",
                value=st.session_state.get("phrase_lock_raw", ""),
                placeholder="另一場生命 → ein anderes Leben\n一個人 → allein",
                height=120,
                key="phrase_lock_input"
            )
        with col2:
            char_voice_raw = st.text_area(
                "Character Voices  (name: description)",
                value=st.session_state.get("char_voice_raw", ""),
                placeholder="Hong: provocative, sharp, self-destructive\nQing: restrained, introspective",
                height=120,
                key="char_voice_input"
            )
        if phrase_lock_raw:
            st.session_state["phrase_lock_raw"] = phrase_lock_raw
        if char_voice_raw:
            st.session_state["char_voice_raw"] = char_voice_raw

    # ─── Input ───────────────────────────────────────────────────────────────
    st.subheader("📥 Input")
    input_method = st.radio("Input method", ["Upload SRT file", "Paste SRT text"], horizontal=True)

    srt_text: Optional[str] = None

    if input_method == "Upload SRT file":
        uploaded = st.file_uploader("Upload .srt file", type=["srt", "txt"])
        if uploaded:
            srt_text = uploaded.read().decode("utf-8", errors="replace")
    else:
        srt_text = st.text_area(
            "Paste SRT content",
            height=220,
            placeholder=(
                "1\n00:01:39,960 --> 00:01:42,200\n因為我想找到那個給青帶來高潮的男人\n\n"
                "2\n00:01:41,320 --> 00:01:46,200\n那個她諱莫如深 不肯透露的男人\n"
            )
        )

    if not srt_text or not srt_text.strip():
        st.info("Upload or paste an SRT file to start the pipeline.")
        return

    segments = SegmentationAgent.parse_srt(srt_text, language=source_lang)
    if not segments:
        st.warning("No valid SRT segments detected. Check the format.")
        return

    st.caption(f"{len(segments)} segments detected — IDs {segments[0].id}–{segments[-1].id}")

    # Batch size selector
    max_batch = min(len(segments), 50)
    batch_size = st.slider(
        "Batch size (segments to process)",
        min_value=1,
        max_value=max_batch,
        value=min(10, max_batch),
        help="Larger batches use more API tokens."
    )
    batch = segments[:batch_size]

    # ─── Run Pipeline ────────────────────────────────────────────────────────
    run_col, clear_col, arc_col = st.columns([3, 1, 1])
    with run_col:
        run_clicked = st.button("🚀 Run Localization Pipeline", type="primary", use_container_width=True)
    with clear_col:
        if st.button("🗑 Clear Results", use_container_width=True):
            st.session_state.pop("loc_results", None)
            st.session_state.pop("loc_arc", None)
            st.rerun()
    with arc_col:
        track_arc = st.checkbox("Track arc", value=False, key="track_arc",
                                help="Track emotional arc across the batch")

    if run_clicked:
        memory = _build_memory_from_form(phrase_lock_raw, char_voice_raw)
        track_arc = st.session_state.get("track_arc", False)
        orchestrator = LocalizationOrchestrator(memory=memory, track_arc=track_arc)

        progress_bar = st.progress(0.0)
        status_text = st.empty()

        def on_progress(current: int, total: int, result: LocalizationResult):
            progress_bar.progress(current / total)
            preview = (result.final or result.selected or "")[:40]
            conf_pct = int(result.tone_confidence * 100)
            status_text.text(
                f"[{current}/{total}] {result.qa_status.upper()} "
                f"| tone: {result.selected_tone} ({conf_pct}%) — {preview}"
            )

        with st.spinner("Running pipeline..."):
            results = orchestrator.process_batch(
                batch,
                target_lang=target_lang,
                translation_mode=mode,
                scene_context=scene_context,
                progress_callback=on_progress,
            )

        progress_bar.progress(1.0)
        approved_n = sum(1 for r in results if r.qa_status == "approved")
        status_text.success(f"Done — {len(results)} segments, {approved_n} approved, {len(results) - approved_n} need review")
        st.session_state["loc_results"] = results
        st.session_state["loc_arc"] = orchestrator.arc_summary()

    # ─── Results ─────────────────────────────────────────────────────────────
    results: List[LocalizationResult] = st.session_state.get("loc_results", [])
    if not results:
        return

    # Summary metrics
    approved_n = sum(1 for r in results if r.qa_status == "approved")
    revise_n = len(results) - approved_n

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Segments", len(results))
    m2.metric("Approved", approved_n)
    m3.metric("Needs Review", revise_n)
    avg_conf = sum(r.tone_confidence for r in results) / len(results) if results else 0
    m4.metric("Avg Confidence", f"{avg_conf:.0%}")

    # ─── Emotional Arc ───────────────────────────────────────────────────────
    arc_data = st.session_state.get("loc_arc")
    if arc_data:
        with st.expander("🎭 Emotional Arc Analysis", expanded=False):
            a1, a2, a3 = st.columns(3)
            a1.metric("Dominant Tone", arc_data.get("dominant_tone", "—"))
            a2.metric("Mean Valence", arc_data.get("mean_valence", "—"))
            a3.metric("Flat Arc Warning", "Yes" if arc_data.get("flat_arc_warning") else "No")
            dist = arc_data.get("tone_distribution", {})
            if dist:
                st.write("**Tone distribution:**", "  ".join(f"`{k}×{v}`" for k, v in sorted(dist.items(), key=lambda x: -x[1])))
            jumps = arc_data.get("tone_jumps", [])
            if jumps:
                st.warning(f"{len(jumps)} tone jump(s) detected:")
                for j in jumps:
                    st.write(f"  #{j['from_id']} → #{j['to_id']}: `{j['from_tone']}` → `{j['to_tone']}` (Δ {j['delta']})")

    # ─── Segment review ──────────────────────────────────────────────────────
    st.subheader("📋 Review")

    show_filter = st.radio("Show", ["All", "Needs Review", "Approved"], horizontal=True)

    for r in results:
        if show_filter == "Approved" and r.qa_status != "approved":
            continue
        if show_filter == "Needs Review" and r.qa_status == "approved":
            continue

        badge = _status_badge(r.qa_status)
        with st.expander(
            f"{badge} #{r.id} — {r.source_text[:50]}{'…' if len(r.source_text) > 50 else ''}",
            expanded=(r.qa_status == "revise")
        ):
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Source")
                st.code(r.source_text, language=None)
                if r.candidates:
                    with st.expander("All candidates", expanded=False):
                        for j, cand in enumerate(r.candidates, 1):
                            st.write(f"{j}. {cand.text}")
            with c2:
                inferred_note = (
                    f" (inferred: {r.inferred_tone})" if r.inferred_tone and r.inferred_tone != r.selected_tone else ""
                )
                conf_pct = int(r.tone_confidence * 100)
                st.caption(f"Translation  •  Tone: **{r.selected_tone}**{inferred_note}  •  Confidence: {conf_pct}%")
                edited = st.text_input(
                    "Edit translation",
                    value=r.final or r.selected,
                    key=f"edit_{r.id}",
                    label_visibility="collapsed"
                )
                r.final = edited
                if r.tone_rationale:
                    st.caption(f"_Director note: {r.tone_rationale}_")
                if r.qa_iterations:
                    st.caption(f"_QA revision loops: {r.qa_iterations}_")

            if r.consistency_changes:
                for ch in r.consistency_changes:
                    if ch:
                        st.caption(f"🔒 Memory: {ch}")

            if r.qa_issues:
                for issue in r.qa_issues:
                    st.warning(f"⚠️ {issue}", icon=None)
            if r.qa_suggestion:
                st.info(f"💡 {r.qa_suggestion}")

    # ─── Export ──────────────────────────────────────────────────────────────
    st.subheader("📦 Export")
    output_agent = OutputAgent()

    ex1, ex2, ex3 = st.columns(3)
    with ex1:
        st.download_button(
            "⬇️ Download SRT",
            data=output_agent.to_srt(results),
            file_name="localized.srt",
            mime="text/plain",
            use_container_width=True
        )
    with ex2:
        st.download_button(
            "⬇️ Download CSV",
            data=output_agent.to_csv(results),
            file_name="localized.csv",
            mime="text/csv",
            use_container_width=True
        )
    with ex3:
        st.download_button(
            "⬇️ Bilingual SRT",
            data=output_agent.to_bilingual_srt(results),
            file_name="bilingual.srt",
            mime="text/plain",
            use_container_width=True
        )
