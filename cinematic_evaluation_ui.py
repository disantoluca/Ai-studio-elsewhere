#!/usr/bin/env python3
"""
Cinematic Evaluation UI
Streamlit interface for the localization evaluation harness.

Four sections:
  Dataset   — create and manage reference cases
  Run       — execute evaluation against the current pipeline
  Review    — human preference capture (pairwise)
  Regression — compare current run against stored baseline
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Optional

import streamlit as st

_AGENTS_DIR = Path(__file__).parent / "agents"
if str(_AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENTS_DIR))

try:
    from localization_evaluator import (
        EvalCase,
        EvalResult,
        DimensionScores,
        DeterministicResult,
        EvaluationRunner,
        RegressionReporter,
        EvalDataset,
        _get_pipeline_version,
        PIPELINE_AVAILABLE,
    )
    from cinematic_localization_agent import (
        LocalizationOrchestrator,
        LocalizationBible,
        LocalizationMemory,
    )
    EVAL_AVAILABLE = True
    _IMPORT_ERROR = ""
except ImportError as e:
    EVAL_AVAILABLE = False
    _IMPORT_ERROR = str(e)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

_DIMENSIONS = DimensionScores.DIMENSIONS if EVAL_AVAILABLE else []
_DIM_LABELS = {
    "meaning_preservation": "Meaning",
    "cinematic_naturalness": "Naturalness",
    "tone_alignment": "Tone",
    "character_voice": "Character Voice",
    "subtitle_fitness": "Subtitle Fitness",
    "context_use": "Context Use",
}


def _score_color(v: float) -> str:
    if v >= 8.0:
        return "green"
    if v >= 6.0:
        return "orange"
    return "red"


def _score_badge(label: str, v: float) -> str:
    return f":{_score_color(v)}[**{label}** {v:.1f}]"


def _delta_badge(dim: str, delta: float) -> str:
    label = _DIM_LABELS.get(dim, dim)
    if delta > 0:
        return f":green[{label}  +{delta:.2f}]"
    if delta < -0.5:
        return f":red[{label}  {delta:.2f}]"
    return f":orange[{label}  {delta:.2f}]"


def _load_orchestrator(project_id: Optional[str] = None) -> Optional["LocalizationOrchestrator"]:
    if not PIPELINE_AVAILABLE:
        return None
    if project_id and LocalizationBible.exists(project_id):
        bible = LocalizationBible.load(project_id)
        memory = bible.to_memory()
    else:
        memory = LocalizationMemory()
    return LocalizationOrchestrator(memory=memory)


# ─────────────────────────────────────────────────────────────────────────────
# Section renderers
# ─────────────────────────────────────────────────────────────────────────────

def _render_dataset_section():
    st.subheader("Reference Dataset")
    st.caption("Each case is one evaluation unit: source, reference, context, traits.")

    ds = EvalDataset()
    cases = ds.list_cases()

    col_new, col_import = st.columns([2, 1])
    with col_new:
        with st.expander("➕ New Case", expanded=not cases):
            _render_new_case_form(ds)
    with col_import:
        with st.expander("📥 Import JSON"):
            raw = st.text_area("Paste case JSON", height=200, key="import_json")
            if st.button("Import", key="do_import"):
                try:
                    d = json.loads(raw)
                    cases_list = d if isinstance(d, list) else [d]
                    for c in cases_list:
                        ds.save(EvalCase.from_dict(c))
                    st.success(f"Imported {len(cases_list)} case(s)")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    if not cases:
        st.info("No cases yet. Create one above, or import the sample dataset.")
        _render_seed_button(ds)
        return

    st.caption(f"{len(cases)} case(s) in dataset")
    for cid in cases:
        case = ds.load(cid)
        if not case:
            continue
        with st.expander(f"`{cid}` — {case.source[:40]}…"):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Source:** {case.source}")
                st.write(f"**Reference:** {case.reference}")
                st.write(f"**Languages:** {case.source_language.upper()} → {case.target_language.upper()}")
            with c2:
                if case.expected_traits:
                    st.write(f"**Expected:** {', '.join(case.expected_traits)}")
                if case.forbidden_traits:
                    st.write(f"**Forbidden:** {', '.join(case.forbidden_traits)}")
                if case.context:
                    st.json(case.context, expanded=False)
            if st.button(f"Delete `{cid}`", key=f"del_{cid}"):
                ds.delete(cid)
                st.rerun()


def _render_new_case_form(ds: "EvalDataset"):
    with st.form("new_case_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            case_id = st.text_input("Case ID", placeholder="bad_bird_001")
            project_id = st.text_input("Project ID", placeholder="bad_bird")
            source = st.text_input("Source text", placeholder="可我覺得賤")
            reference = st.text_input("Reference translation", placeholder="Aber ich fühle mich schäbig")
        with col2:
            src_lang = st.selectbox("Source lang", ["zh", "en", "fr", "ja", "ko"])
            tgt_lang = st.selectbox("Target lang", ["de", "en", "fr", "ja", "es", "it"])
            mood = st.text_input("Scene mood", placeholder="raw, self-aware, bitter")
            speaker = st.text_input("Speaker", placeholder="Hong")
            emotion = st.text_input("Emotional state", placeholder="self-disgust")

        col3, col4 = st.columns(2)
        with col3:
            expected = st.text_input("Expected traits (comma-separated)",
                                      placeholder="spoken German, emotionally direct")
        with col4:
            forbidden = st.text_input("Forbidden traits (comma-separated)",
                                       placeholder="literal but unnatural, overly polite")

        submitted = st.form_submit_button("Save Case")
        if submitted and case_id and source and reference:
            case = EvalCase(
                case_id=case_id,
                project_id=project_id or "default",
                source=source,
                reference=reference,
                source_language=src_lang,
                target_language=tgt_lang,
                context={
                    "project": {},
                    "scene": {"mood": mood} if mood else {},
                    "segment": {k: v for k, v in [("speaker", speaker), ("emotional_state", emotion)] if v},
                },
                expected_traits=[t.strip() for t in expected.split(",") if t.strip()],
                forbidden_traits=[t.strip() for t in forbidden.split(",") if t.strip()],
            )
            ds.save(case)
            st.success(f"Case `{case_id}` saved.")
        elif submitted:
            st.warning("Case ID, source, and reference are required.")


def _render_seed_button(ds: "EvalDataset"):
    if st.button("🌱 Load sample cases (Bad Bird film)"):
        samples = [
            EvalCase(
                case_id="bad_bird_001",
                project_id="bad_bird",
                source="可我覺得賤",
                reference="Aber ich fühle mich schäbig",
                source_language="zh",
                target_language="de",
                context={"project": {}, "scene": {"mood": "raw, self-aware, bitter"},
                         "segment": {"speaker": "Hong", "emotional_state": "self-disgust"}},
                expected_traits=["spoken German", "emotionally direct", "not euphemistic"],
                forbidden_traits=["literal but unnatural", "overly polite"],
            ),
            EvalCase(
                case_id="bad_bird_002",
                project_id="bad_bird",
                source="那個她諱莫如深 不肯透露的男人",
                reference="Den Mann, über den sie beharrlich schweigt",
                source_language="zh",
                target_language="de",
                context={"project": {}, "scene": {"mood": "intimate, charged"},
                         "segment": {"speaker": "Hong", "emotional_state": "restrained jealousy"}},
                expected_traits=["weight of silence", "understated", "no melodrama"],
                forbidden_traits=["over-explanation", "literal 'keeps secret'"],
            ),
            EvalCase(
                case_id="bad_bird_003",
                project_id="bad_bird",
                source="帥呆了",
                reference="Total heiß",
                source_language="zh",
                target_language="de",
                context={"project": {}, "scene": {"mood": "ironic, self-aware"},
                         "segment": {"speaker": "Hong", "emotional_state": "detached irony"}},
                expected_traits=["colloquial", "punchy", "ironic register"],
                forbidden_traits=["formal", "long explanation", "adjective list"],
            ),
        ]
        for c in samples:
            ds.save(c)
        st.success("3 sample cases loaded.")
        st.rerun()


def _render_run_section():
    st.subheader("Run Evaluation")
    st.caption(f"Current pipeline version: `{_get_pipeline_version()}`")

    ds = EvalDataset()
    all_ids = ds.list_cases()

    if not all_ids:
        st.info("No cases in dataset. Add cases in the Dataset tab first.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        selected_ids = st.multiselect("Select cases", all_ids, default=all_ids[:min(5, len(all_ids))])
    with col2:
        project_id = st.text_input("Project ID (for bible memory)", placeholder="bad_bird")
        mode = st.selectbox("Translation mode", ["cinematic", "literal", "festival-safe", "edgy"])
    with col3:
        run_rubric = st.checkbox("Run LLM rubric scoring", value=True,
                                  help="Disabling skips LLM calls — deterministic checks only")

    if not selected_ids:
        st.info("Select at least one case.")
        return

    run_clicked = st.button("▶️ Run Evaluation", type="primary")

    if run_clicked:
        cases = [c for c in (ds.load(i) for i in selected_ids) if c]
        orchestrator = _load_orchestrator(project_id or None)
        if not orchestrator:
            st.error("Pipeline not available.")
            return

        runner = EvaluationRunner()
        progress = st.progress(0.0)
        status = st.empty()

        def on_prog(i, total, result):
            progress.progress(i / total)
            det_ok = "✅" if (result.deterministic and result.deterministic.passed) else "❌"
            status.text(f"[{i}/{total}] {det_ok} {result.case_id} — {result.candidate[:40]}")

        with st.spinner("Running..."):
            results = runner.run_batch(cases, orchestrator, mode, run_rubric, on_prog)

        progress.progress(1.0)
        st.session_state["eval_results"] = results
        st.session_state["eval_run_complete"] = True
        passed = sum(1 for r in results if r.deterministic and r.deterministic.passed)
        st.success(f"Done — {len(results)} cases, {passed}/{len(results)} passed deterministic checks")

    results: List[EvalResult] = st.session_state.get("eval_results", [])
    if not results:
        return

    # Results table
    st.divider()
    for r in results:
        det_icon = "✅" if (r.deterministic and r.deterministic.passed) else "❌"
        with st.expander(f"{det_icon} `{r.case_id}`", expanded=not (r.deterministic and r.deterministic.passed)):
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Source / Reference")
                st.write(r.source)
                st.write(f"**Reference:** {r.reference}")
            with c2:
                st.caption("Candidate")
                st.write(f"**Output:** {r.candidate}")

            if r.deterministic and r.deterministic.failed_checks:
                for fc in r.deterministic.failed_checks:
                    st.warning(f"⚠️ {fc}")

            if r.scores:
                st.caption("Dimension Scores")
                cols = st.columns(len(_DIMENSIONS))
                for col, dim in zip(cols, _DIMENSIONS):
                    v = getattr(r.scores, dim)
                    col.metric(_DIM_LABELS[dim], f"{v:.1f}")
                if r.scores.rationales:
                    with st.expander("Evaluator rationales"):
                        for dim, rationale in r.scores.rationales.items():
                            st.write(f"**{_DIM_LABELS.get(dim, dim)}:** {rationale}")


def _render_review_section():
    st.subheader("Human Review")
    st.caption("Pairwise comparison — more reliable than numerical scores for artistic judgment.")

    results: List[EvalResult] = st.session_state.get("eval_results", [])
    if not results:
        st.info("Run an evaluation first.")
        return

    # Load preferences from session
    prefs: dict = st.session_state.get("human_prefs", {})

    reviewed = sum(1 for r in results if prefs.get(r.case_id, ""))
    st.caption(f"{reviewed}/{len(results)} reviewed")

    for r in results:
        with st.expander(
            f"`{r.case_id}` {'✓' if prefs.get(r.case_id) else '○'}",
            expanded=not prefs.get(r.case_id)
        ):
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Reference")
                st.info(r.reference)
            with c2:
                st.caption("Candidate")
                st.info(r.candidate)
            st.caption(f"Source: {r.source}")

            current = prefs.get(r.case_id, "")
            choice = st.radio(
                "Preference",
                ["candidate", "reference", "no_preference", "unsure"],
                index=["candidate", "reference", "no_preference", "unsure"].index(current) if current else 0,
                horizontal=True,
                key=f"pref_{r.case_id}",
                format_func=lambda x: {
                    "candidate": "New (Candidate)",
                    "reference": "Reference",
                    "no_preference": "Tie",
                    "unsure": "Unsure",
                }[x],
            )
            prefs[r.case_id] = choice
            r.human_preference = choice

    st.session_state["human_prefs"] = prefs

    if st.button("💾 Save Preferences to Results"):
        for r in results:
            r.human_preference = prefs.get(r.case_id, "")
        st.session_state["eval_results"] = results
        st.success("Preferences saved to current run.")


def _render_regression_section():
    st.subheader("Regression Report")
    st.caption("Compare current run against a stored baseline. Hard gates block release; soft gates warn.")

    reporter = RegressionReporter()
    results: List[EvalResult] = st.session_state.get("eval_results", [])
    baselines = reporter.list_baselines()

    col1, col2 = st.columns(2)
    with col1:
        baseline_label = st.selectbox(
            "Compare against baseline",
            ["(none)"] + baselines,
            index=0,
        )
    with col2:
        save_label = st.text_input(
            "Save current run as baseline",
            placeholder=f"{_get_pipeline_version()}_initial",
        )
        if st.button("💾 Save as Baseline") and save_label and results:
            path = reporter.save_baseline(results, save_label)
            st.success(f"Saved: `{os.path.basename(path)}`")
            st.rerun()

    if not results:
        st.info("Run an evaluation first.")
        return

    compare_against = baseline_label if baseline_label != "(none)" else None
    report = reporter.generate(results, compare_against)

    st.divider()

    # Gate banners
    if report["hard_gate_passed"]:
        st.success("✅ Hard gate: PASSED — no structural failures")
    else:
        st.error(f"❌ Hard gate: FAILED — {len(report['hard_failures'])} failure(s)")
        for f in report["hard_failures"]:
            st.write(f"  • `{f['case_id']}` — {f['check']}: {f['detail']}")

    if compare_against:
        if report["soft_gate_passed"]:
            st.success("✅ Soft gate: PASSED — no material regressions")
        else:
            st.warning("⚠️ Soft gate: FAILED — dimension regression detected")
            for dim, detail in report["soft_gate_details"].items():
                st.write(f"  • {_DIM_LABELS.get(dim, dim)}: {detail}")

    st.divider()

    # Dimension scores + deltas
    st.subheader("Dimension Scores")
    avgs = report.get("dimension_averages", {})
    deltas = report.get("dimension_deltas", {})

    if avgs:
        cols = st.columns(len(avgs))
        for col, (dim, v) in zip(cols, avgs.items()):
            delta = deltas.get(dim)
            col.metric(
                _DIM_LABELS.get(dim, dim),
                f"{v:.2f}",
                delta=f"{delta:+.2f}" if delta is not None else None,
                delta_color="normal",
            )

    # Human preference
    pref = report.get("human_preference", {})
    total = sum(pref.values())
    if total > 0:
        st.divider()
        st.subheader("Human Preference")
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("New (Candidate)", f"{pref.get('candidate', 0):.0%}")
        p2.metric("Reference", f"{pref.get('reference', 0):.0%}")
        p3.metric("Tie", f"{pref.get('no_preference', 0):.0%}")
        p4.metric("Unsure", f"{pref.get('unsure', 0):.0%}")

    # Save report
    st.divider()
    if st.button("📄 Save Report"):
        path = reporter.save_report(report)
        st.success(f"Report saved: `{os.path.basename(path)}`")
        with st.expander("Report JSON"):
            st.json(report)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def display_evaluation_ui():
    st.header("🔬 Localization Evaluation Harness")
    st.caption(
        "Evidence, not intuition.  "
        "Reference Dataset → Pipeline → Dimension Scores → Regression Report"
    )

    if not EVAL_AVAILABLE:
        st.error(f"Evaluation module unavailable: {_IMPORT_ERROR}")
        return

    tab_ds, tab_run, tab_review, tab_reg = st.tabs([
        "📋 Dataset",
        "▶️ Run",
        "👁 Human Review",
        "📊 Regression",
    ])

    with tab_ds:
        _render_dataset_section()
    with tab_run:
        _render_run_section()
    with tab_review:
        _render_review_section()
    with tab_reg:
        _render_regression_section()
