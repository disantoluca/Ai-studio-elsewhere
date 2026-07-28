#!/usr/bin/env python3
"""
Cinematic Localization Evaluator
Evaluation harness — completely outside the production pipeline.

Three evaluation modes:
  1. Deterministic checks  — structural validation, no LLM required
  2. Rubric scoring        — LLM evaluator, blind to pipeline version
  3. Regression reporting  — compare current run against stored baseline

Question this answers: did this code, prompt, or model change make
localization better or worse — and on which dimension specifically?
"""

import json
import os
import re
import subprocess
from dataclasses import dataclass, field, fields as _dc_fields
from datetime import datetime
from typing import Dict, List, Optional

try:
    from cinematic_localization_agent import (
        LocalizationOrchestrator,
        SubtitleSegment,
        ProjectContext,
        SceneContext,
        SegmentContext,
        DimensionScores as _PipelineDimScores,  # may not exist yet — handled below
        _llm,
    )
    PIPELINE_AVAILABLE = True
except ImportError:
    PIPELINE_AVAILABLE = False

# ── Directory layout ─────────────────────────────────────────────────────────

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL_DIR = os.path.join(_ROOT, "data", "localization", "eval")
CASES_DIR = os.path.join(EVAL_DIR, "cases")
REPORTS_DIR = os.path.join(EVAL_DIR, "reports")
BASELINES_DIR = os.path.join(EVAL_DIR, "baselines")


def _ensure_dirs():
    for d in [CASES_DIR, REPORTS_DIR, BASELINES_DIR]:
        os.makedirs(d, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EvalCase:
    """
    One evaluation unit. Maps directly to the spec JSON format.
    The context dict uses the same tier structure as the pipeline:
      {"project": {...}, "scene": {...}, "segment": {...}}
    """
    case_id: str
    project_id: str
    source: str
    reference: str
    source_language: str = "zh"
    target_language: str = "de"
    context: Dict = field(default_factory=lambda: {"project": {}, "scene": {}, "segment": {}})
    required_phrase_locks: List[str] = field(default_factory=list)
    expected_traits: List[str] = field(default_factory=list)
    forbidden_traits: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            "case_id": self.case_id,
            "project_id": self.project_id,
            "source": self.source,
            "reference": self.reference,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "context": self.context,
            "required_phrase_locks": self.required_phrase_locks,
            "expected_traits": self.expected_traits,
            "forbidden_traits": self.forbidden_traits,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "EvalCase":
        valid = {f.name for f in _dc_fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})


@dataclass
class DeterministicResult:
    """Results of structural/technical checks that require no LLM."""
    case_id: str
    no_empty_output: bool = True
    phrase_locks_applied: bool = True
    line_length_ok: bool = True
    reading_speed_ok: bool = True
    no_forbidden_literals: bool = True
    details: Dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all([
            self.no_empty_output,
            self.phrase_locks_applied,
            self.line_length_ok,
            self.reading_speed_ok,
            self.no_forbidden_literals,
        ])

    @property
    def failed_checks(self) -> List[str]:
        mapping = {
            "no_empty_output": "Empty output",
            "phrase_locks_applied": "Phrase lock missing",
            "line_length_ok": "Line too long",
            "reading_speed_ok": "Too fast to read",
            "no_forbidden_literals": "Forbidden pattern found",
        }
        return [label for attr, label in mapping.items() if not getattr(self, attr)]


@dataclass
class DimensionScores:
    """
    Per-dimension artistic quality scores (0.0–10.0).
    Never aggregated into a single number — a regression on tone can hide
    behind an improvement in literal accuracy if averaged.
    """
    meaning_preservation: float = 0.0
    cinematic_naturalness: float = 0.0
    tone_alignment: float = 0.0
    character_voice: float = 0.0
    subtitle_fitness: float = 0.0
    context_use: float = 0.0
    rationales: Dict[str, str] = field(default_factory=dict)

    DIMENSIONS = [
        "meaning_preservation",
        "cinematic_naturalness",
        "tone_alignment",
        "character_voice",
        "subtitle_fitness",
        "context_use",
    ]

    def to_dict(self) -> Dict:
        return {d: round(getattr(self, d), 2) for d in self.DIMENSIONS} | {"rationales": self.rationales}

    @classmethod
    def from_dict(cls, d: Dict) -> "DimensionScores":
        obj = cls()
        for dim in cls.DIMENSIONS:
            setattr(obj, dim, float(d.get(dim, 0.0)))
        obj.rationales = d.get("rationales", {})
        return obj


@dataclass
class EvalResult:
    case_id: str
    pipeline_version: str
    source: str
    reference: str
    candidate: str
    deterministic: Optional[DeterministicResult] = None
    scores: Optional[DimensionScores] = None
    human_preference: str = ""   # "candidate" | "reference" | "no_preference" | "unsure"
    timestamp: str = ""

    def to_dict(self) -> Dict:
        return {
            "case_id": self.case_id,
            "pipeline_version": self.pipeline_version,
            "source": self.source,
            "reference": self.reference,
            "candidate": self.candidate,
            "deterministic": {
                "passed": self.deterministic.passed if self.deterministic else None,
                "failed_checks": self.deterministic.failed_checks if self.deterministic else [],
                "details": self.deterministic.details if self.deterministic else {},
            },
            "scores": self.scores.to_dict() if self.scores else None,
            "human_preference": self.human_preference,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "EvalResult":
        r = cls(
            case_id=d["case_id"],
            pipeline_version=d.get("pipeline_version", "unknown"),
            source=d.get("source", ""),
            reference=d.get("reference", ""),
            candidate=d.get("candidate", ""),
            human_preference=d.get("human_preference", ""),
            timestamp=d.get("timestamp", ""),
        )
        if d.get("scores"):
            r.scores = DimensionScores.from_dict(d["scores"])
        return r


# ─────────────────────────────────────────────────────────────────────────────
# Mode 1 — Deterministic Checker
# ─────────────────────────────────────────────────────────────────────────────

class DeterministicChecker:
    """
    Structural validation. No LLM. Runs before rubric scoring.
    Hard gate failures here block the pipeline from shipping.
    """

    MAX_LINE_CHARS = 42
    MAX_CHARS_PER_SEC = 17.0

    def check(
        self,
        case: EvalCase,
        candidate: str,
        start_tc: str = "00:00:01,000",
        end_tc: str = "00:00:04,000",
    ) -> DeterministicResult:
        result = DeterministicResult(case_id=case.case_id)

        # Empty output
        if not candidate or not candidate.strip():
            result.no_empty_output = False
            result.details["empty_output"] = "Output is empty or whitespace-only"
            return result  # no further checks make sense

        # Phrase locks
        for lock in case.required_phrase_locks:
            if lock not in candidate:
                result.phrase_locks_applied = False
                result.details[f"phrase_lock"] = f"Required '{lock}' not found in output"

        # Line length
        for i, line in enumerate(candidate.split("\n")):
            if len(line) > self.MAX_LINE_CHARS:
                result.line_length_ok = False
                result.details[f"line_length_{i}"] = (
                    f"Line {i+1}: {len(line)} chars (max {self.MAX_LINE_CHARS})"
                )

        # Reading speed
        dur = self._tc_to_sec(end_tc) - self._tc_to_sec(start_tc)
        if dur > 0:
            cps = len(candidate.replace("\n", " ")) / dur
            if cps > self.MAX_CHARS_PER_SEC:
                result.reading_speed_ok = False
                result.details["reading_speed"] = (
                    f"{cps:.1f} chars/sec (max {self.MAX_CHARS_PER_SEC})"
                )

        return result

    @staticmethod
    def _tc_to_sec(tc: str) -> float:
        m = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)", tc)
        if m:
            h, mm, s, sub = m.groups()
            return int(h) * 3600 + int(mm) * 60 + int(s) + int(sub.ljust(3, "0")[:3]) / 1000.0
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Mode 2 — Rubric Scorer (LLM, blind to pipeline version)
# ─────────────────────────────────────────────────────────────────────────────

class RubricScorer:
    """
    LLM evaluator. Scores 6 artistic dimensions independently.
    The evaluator receives source, reference, context, and candidate —
    but NEVER the pipeline version or any metadata that could cause bias.
    """

    SYSTEM = (
        "You are a professional film localization evaluator. "
        "You assess subtitle quality across specific independent dimensions. "
        "You do NOT know which pipeline version produced the candidate. "
        "Evaluate the candidate on its own merits against source, reference, and context. "
        "\n\n"
        "Score each dimension 0.0–10.0 independently. Do NOT average them. "
        "A regression on tone must remain visible even when literal accuracy improves. "
        "\n\n"
        "Dimensions:\n"
        "- meaning_preservation: Does the candidate preserve the source meaning and all implications?\n"
        "- cinematic_naturalness: Does it sound like spoken dialogue — not translated text?\n"
        "- tone_alignment: Does it match the provided scene/character/segment direction?\n"
        "- character_voice: Is it consistent with how this character speaks? Score 5 if character unknown.\n"
        "- subtitle_fitness: Appropriate length, natural line breaks, suitable for display?\n"
        "- context_use: Did the supplied context (mood, speaker, purpose) visibly influence the output?\n"
        "\n"
        "Respond ONLY with valid JSON. No markdown. No extra text."
    )

    def score(self, case: EvalCase, candidate: str) -> DimensionScores:
        user = (
            f"Source ({case.source_language.upper()}): {case.source}\n"
            f"Reference ({case.target_language.upper()}): {case.reference}\n"
            f"Candidate ({case.target_language.upper()}): {candidate}\n"
        )
        if case.context and any(case.context.values()):
            user += f"\nContext:\n{json.dumps(case.context, ensure_ascii=False, indent=2)}\n"
        if case.expected_traits:
            user += f"\nExpected traits: {', '.join(case.expected_traits)}\n"
        if case.forbidden_traits:
            user += f"\nForbidden traits: {', '.join(case.forbidden_traits)}\n"

        user += (
            "\nReturn JSON with keys: "
            "meaning_preservation, cinematic_naturalness, tone_alignment, "
            "character_voice, subtitle_fitness, context_use (all 0.0–10.0), "
            'and "rationales": {"dimension": "one sentence each"}'
        )

        raw = _llm.call(self.SYSTEM, user, max_tokens=600)
        return self._parse(raw)

    def _parse(self, raw: str) -> DimensionScores:
        try:
            cleaned = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("```")
            data = json.loads(cleaned)
            return DimensionScores.from_dict(data)
        except Exception:
            return DimensionScores()


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation Runner — wires case → pipeline → scores
# ─────────────────────────────────────────────────────────────────────────────

def _get_pipeline_version() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_ROOT,
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "unknown"


def _dict_to_ctx(cls, d: Dict):
    """Safely instantiate a context dataclass from a dict, ignoring unknown keys."""
    valid = {f.name for f in _dc_fields(cls)}
    return cls(**{k: v for k, v in d.items() if k in valid}) if d else None


class EvaluationRunner:
    def __init__(self):
        self.checker = DeterministicChecker()
        self.scorer = RubricScorer()

    def run_case(
        self,
        case: EvalCase,
        orchestrator: "LocalizationOrchestrator",
        mode: str = "cinematic",
        run_rubric: bool = True,
    ) -> EvalResult:
        """
        Run a single eval case through the pipeline and score the output.
        pipeline_version is captured from git — the scorer never sees it.
        """
        project_ctx = _dict_to_ctx(ProjectContext, case.context.get("project") or {})
        scene_ctx = _dict_to_ctx(SceneContext, case.context.get("scene") or {})
        segment_ctx = _dict_to_ctx(SegmentContext, case.context.get("segment") or {})

        seg = SubtitleSegment(
            id=1,
            start="00:00:01,000",
            end="00:00:04,000",
            source_text=case.source,
            language=case.source_language,
        )

        pipeline_results = orchestrator.process_batch(
            [seg],
            target_lang=case.target_language.upper(),
            translation_mode=mode,
            project_ctx=project_ctx if (project_ctx and not project_ctx.is_empty()) else None,
            scene_ctx=scene_ctx if (scene_ctx and not scene_ctx.is_empty()) else None,
            segment_ctx=segment_ctx if (segment_ctx and not segment_ctx.is_empty()) else None,
        )
        candidate = (pipeline_results[0].final or pipeline_results[0].selected) if pipeline_results else ""

        det = self.checker.check(case, candidate, seg.start, seg.end)
        scores = self.scorer.score(case, candidate) if (run_rubric and candidate) else None

        return EvalResult(
            case_id=case.case_id,
            pipeline_version=_get_pipeline_version(),
            source=case.source,
            reference=case.reference,
            candidate=candidate,
            deterministic=det,
            scores=scores,
            timestamp=datetime.now().isoformat(timespec="seconds"),
        )

    def run_batch(
        self,
        cases: List[EvalCase],
        orchestrator: "LocalizationOrchestrator",
        mode: str = "cinematic",
        run_rubric: bool = True,
        progress_callback=None,
    ) -> List[EvalResult]:
        results = []
        for i, case in enumerate(cases):
            result = self.run_case(case, orchestrator, mode, run_rubric)
            results.append(result)
            if progress_callback:
                progress_callback(i + 1, len(cases), result)
        return results


# ─────────────────────────────────────────────────────────────────────────────
# Mode 3 — Regression Reporter
# ─────────────────────────────────────────────────────────────────────────────

class RegressionReporter:
    """
    Compares a current evaluation run against a stored baseline.
    Separates hard gates (must not regress) from soft gates (should not regress).
    """

    # Soft gate: any dimension declining more than this triggers a warning
    SOFT_GATE_DELTA = -0.5

    def save_baseline(self, results: List[EvalResult], label: str) -> str:
        _ensure_dirs()
        path = os.path.join(BASELINES_DIR, f"{label}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in results], f, ensure_ascii=False, indent=2)
        return path

    def load_baseline(self, label: str) -> List[Dict]:
        path = os.path.join(BASELINES_DIR, f"{label}.json")
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_baselines(self) -> List[str]:
        _ensure_dirs()
        return sorted(f[:-5] for f in os.listdir(BASELINES_DIR) if f.endswith(".json"))

    def generate(
        self,
        current: List[EvalResult],
        baseline_label: Optional[str] = None,
    ) -> Dict:
        version = current[0].pipeline_version if current else "unknown"

        # ── Hard gate: deterministic failures ────────────────────────────────
        hard_failures = []
        for r in current:
            if r.deterministic and not r.deterministic.passed:
                for check in r.deterministic.failed_checks:
                    hard_failures.append({"case_id": r.case_id, "check": check,
                                          "detail": str(r.deterministic.details)})

        # ── Current dimension averages ────────────────────────────────────────
        scored = [r for r in current if r.scores]
        current_avgs: Dict[str, float] = {}
        if scored:
            for dim in DimensionScores.DIMENSIONS:
                current_avgs[dim] = round(
                    sum(getattr(r.scores, dim) for r in scored) / len(scored), 2
                )

        # ── Baseline comparison ───────────────────────────────────────────────
        dimension_deltas: Dict[str, float] = {}
        baseline_avgs: Dict[str, float] = {}
        if baseline_label:
            baseline_data = self.load_baseline(baseline_label)
            baseline_scored = [d for d in baseline_data if d.get("scores")]
            if baseline_scored:
                for dim in DimensionScores.DIMENSIONS:
                    baseline_avgs[dim] = round(
                        sum(d["scores"].get(dim, 0) for d in baseline_scored) / len(baseline_scored), 2
                    )
                for dim in DimensionScores.DIMENSIONS:
                    if dim in current_avgs and dim in baseline_avgs:
                        dimension_deltas[dim] = round(current_avgs[dim] - baseline_avgs[dim], 2)

        # ── Human preference ─────────────────────────────────────────────────
        pref = {"candidate": 0, "reference": 0, "no_preference": 0, "unsure": 0}
        for r in current:
            if r.human_preference in pref:
                pref[r.human_preference] += 1
        total_pref = sum(pref.values())
        pref_pct = {k: round(v / total_pref, 2) if total_pref else 0.0 for k, v in pref.items()}

        # ── Soft gates ───────────────────────────────────────────────────────
        soft_gate_details: Dict[str, str] = {}
        passed_soft = True
        for dim, delta in dimension_deltas.items():
            if delta < self.SOFT_GATE_DELTA:
                passed_soft = False
                soft_gate_details[dim] = f"{delta:+.2f} (threshold {self.SOFT_GATE_DELTA})"
        cand_pct = pref_pct.get("candidate", 0)
        ref_pct = pref_pct.get("reference", 0)
        if total_pref >= 5 and ref_pct > cand_pct + 0.20:
            passed_soft = False
            soft_gate_details["human_preference"] = (
                f"Reference preferred {ref_pct:.0%} vs candidate {cand_pct:.0%}"
            )

        return {
            "pipeline_version": version,
            "baseline_version": baseline_label or "none",
            "total_cases": len(current),
            "hard_gate_passed": len(hard_failures) == 0,
            "hard_failures": hard_failures,
            "dimension_averages": current_avgs,
            "dimension_deltas": dimension_deltas,
            "human_preference": pref_pct,
            "soft_gate_passed": passed_soft,
            "soft_gate_details": soft_gate_details,
        }

    def save_report(self, report: Dict) -> str:
        _ensure_dirs()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(REPORTS_DIR, f"{report['pipeline_version']}_{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return path

    def list_reports(self) -> List[str]:
        _ensure_dirs()
        return sorted(
            (f[:-5] for f in os.listdir(REPORTS_DIR) if f.endswith(".json")),
            reverse=True
        )


# ─────────────────────────────────────────────────────────────────────────────
# Dataset Manager
# ─────────────────────────────────────────────────────────────────────────────

class EvalDataset:
    def save(self, case: EvalCase):
        _ensure_dirs()
        path = os.path.join(CASES_DIR, f"{case.case_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(case.to_dict(), f, ensure_ascii=False, indent=2)

    def load(self, case_id: str) -> Optional[EvalCase]:
        path = os.path.join(CASES_DIR, f"{case_id}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return EvalCase.from_dict(json.load(f))
        return None

    def list_cases(self, project_id: Optional[str] = None) -> List[str]:
        _ensure_dirs()
        ids = [f[:-5] for f in os.listdir(CASES_DIR) if f.endswith(".json")]
        if project_id:
            ids = [i for i in ids if i.startswith(project_id)]
        return sorted(ids)

    def load_all(self, project_id: Optional[str] = None) -> List[EvalCase]:
        return [c for c in (self.load(i) for i in self.list_cases(project_id)) if c]

    def delete(self, case_id: str):
        path = os.path.join(CASES_DIR, f"{case_id}.json")
        if os.path.exists(path):
            os.remove(path)
