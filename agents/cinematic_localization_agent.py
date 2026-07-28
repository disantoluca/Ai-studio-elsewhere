#!/usr/bin/env python3
"""
Cinematic Localization Agent
Six-stage agentic pipeline for film-grade subtitle translation.

Pipeline:
  Segmentation → Translation → Tone Calibration → Consistency → QA → Output

Each stage is a separate class with a single responsibility.
The Orchestrator wires them together and passes a context window between stages.
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    import anthropic as _anthropic_lib
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from openai import OpenAI as _OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SubtitleSegment:
    id: int
    start: str          # "HH:MM:SS:FF" | "HH:MM:SS,mmm" | "HH:MM:SS.mmm"
    end: str
    source_text: str
    language: str = "zh"


@dataclass
class TranslationCandidate:
    text: str
    tone_hint: str = "neutral"  # hint from translation agent; overridden by tone agent


@dataclass
class LocalizationResult:
    id: int
    start: str
    end: str
    source_text: str
    candidates: List[TranslationCandidate] = field(default_factory=list)
    candidate_scores: List[float] = field(default_factory=list)   # per-candidate voice alignment
    selected: str = ""
    selected_tone: str = ""
    inferred_tone: str = ""    # pre-LLM tone inference from context rules
    tone_rationale: str = ""
    tone_confidence: float = 0.0
    consistency_changes: List[str] = field(default_factory=list)
    final: str = ""
    qa_status: str = "pending"      # "pending" | "approved" | "revise"
    qa_issues: List[str] = field(default_factory=list)
    qa_suggestion: str = ""
    qa_iterations: int = 0          # how many QA revision loops ran


# ─────────────────────────────────────────────────────────────────────────────
# Memory / Consistency State
# ─────────────────────────────────────────────────────────────────────────────

class LocalizationMemory:
    """
    Central memory layer. Must be shared across all segments in a batch.
    Without this, tone drift will happen across the film.
    """

    def __init__(self):
        self.phrase_lock: Dict[str, str] = {}
        self.character_voice: Dict[str, str] = {}
        self.style_rules: Dict[str, object] = {
            "avoid_literal": True,
            "prefer_short_lines": True,
            "cinematic_tone": True
        }

    def to_dict(self) -> Dict:
        return {
            "phrase_lock": self.phrase_lock,
            "character_voice": self.character_voice,
            "style_rules": self.style_rules
        }

    def from_dict(self, d: Dict) -> "LocalizationMemory":
        self.phrase_lock = d.get("phrase_lock", {})
        self.character_voice = d.get("character_voice", {})
        self.style_rules = {**self.style_rules, **d.get("style_rules", {})}
        return self

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def load(self, path: str) -> "LocalizationMemory":
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.from_dict(json.load(f))
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Localization Bible — durable project-level memory
# ─────────────────────────────────────────────────────────────────────────────

from datetime import datetime as _dt

BIBLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "localization")


class LocalizationBible:
    """
    Durable localization bible — one file per film project.

    Rule: may be edited between batches, frozen during a batch run.
    The memory layer (LocalizationMemory) is extracted from the bible
    before each batch and passed to the orchestrator read-only.
    """

    VERSION = 1

    def __init__(
        self,
        project_id: str,
        source_language: str = "zh",
        target_language: str = "de",
    ):
        self.project_id = project_id
        self.source_language = source_language
        self.target_language = target_language
        self.phrase_locks: Dict[str, str] = {}
        self.character_voices: Dict[str, str] = {}
        self.style_rules: Dict[str, object] = {
            "avoid_literal": True,
            "prefer_short_lines": True,
            "cinematic_tone": True,
        }
        self.director_notes: Dict[str, str] = {}
        self.version: int = self.VERSION
        self.updated_at: str = ""

    # ── Serialization ────────────────────────────────────────────────────────

    def to_dict(self) -> Dict:
        return {
            "project_id": self.project_id,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "phrase_locks": self.phrase_locks,
            "character_voices": self.character_voices,
            "style_rules": self.style_rules,
            "director_notes": self.director_notes,
            "version": self.version,
            "updated_at": self.updated_at,
        }

    def from_dict(self, d: Dict) -> "LocalizationBible":
        self.project_id = d.get("project_id", self.project_id)
        self.source_language = d.get("source_language", self.source_language)
        self.target_language = d.get("target_language", self.target_language)
        self.phrase_locks = d.get("phrase_locks", {})
        self.character_voices = d.get("character_voices", {})
        self.style_rules = {**self.style_rules, **d.get("style_rules", {})}
        self.director_notes = d.get("director_notes", {})
        self.version = d.get("version", self.VERSION)
        self.updated_at = d.get("updated_at", "")
        return self

    # ── Persistence ──────────────────────────────────────────────────────────

    @staticmethod
    def _path(project_id: str) -> str:
        os.makedirs(BIBLE_DIR, exist_ok=True)
        return os.path.join(BIBLE_DIR, f"{project_id}.json")

    def save(self) -> str:
        self.updated_at = _dt.now().isoformat(timespec="seconds")
        path = self._path(self.project_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return path

    @classmethod
    def load(cls, project_id: str) -> "LocalizationBible":
        bible = cls(project_id)
        path = cls._path(project_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                bible.from_dict(json.load(f))
        return bible

    @classmethod
    def list_projects(cls) -> List[str]:
        os.makedirs(BIBLE_DIR, exist_ok=True)
        return sorted(
            f[:-5] for f in os.listdir(BIBLE_DIR) if f.endswith(".json")
        )

    @classmethod
    def exists(cls, project_id: str) -> bool:
        return os.path.exists(cls._path(project_id))

    # ── Memory extraction ────────────────────────────────────────────────────

    def to_memory(self) -> LocalizationMemory:
        """Extract a frozen LocalizationMemory snapshot for pipeline use."""
        mem = LocalizationMemory()
        mem.phrase_lock = dict(self.phrase_locks)
        mem.character_voice = dict(self.character_voices)
        mem.style_rules = dict(self.style_rules)
        return mem


# ─────────────────────────────────────────────────────────────────────────────
# Tone Inference — rule-based pre-LLM step
# ─────────────────────────────────────────────────────────────────────────────

# Keyword → tone mapping (expanded per project via config)
_TONE_SIGNALS: Dict[str, str] = {
    # zh signals
    "賤": "raw",
    "死": "cold",
    "愛": "tender",
    "諱莫如深": "intimate",
    "高潮": "provocative",
    "帥": "ironic",
    "恨": "cold",
    "笑": "tender",
    # scene mood → tone
    "confrontational": "cold",
    "intimate": "intimate",
    "ironic": "ironic",
    "tender": "tender",
    "raw": "raw",
    "bitter": "raw",
    "provocative": "provocative",
}

_CHARACTER_TONE_MAP: Dict[str, str] = {
    "provocative": "provocative",
    "sharp": "cold",
    "restrained": "restrained",
    "introspective": "intimate",
    "self-destructive": "raw",
    "ironic": "ironic",
}


def infer_tone(
    segment: "SubtitleSegment",
    scene_context: Optional[Dict],
    memory: Optional["LocalizationMemory"] = None
) -> str:
    """
    Rule-based tone inference — runs BEFORE the LLM director call.
    Provides a starting hypothesis that the tone agent can override.

    Priority: character_voice override > source text signals > scene mood.
    """
    ctx = scene_context or {}
    char = ctx.get("character", "")

    # 1. Character voice override from memory
    if memory and char and char in memory.character_voice:
        voice_desc = memory.character_voice[char].lower()
        for trait, mapped_tone in _CHARACTER_TONE_MAP.items():
            if trait in voice_desc:
                return mapped_tone

    # 2. Source text keyword signals
    for keyword, tone in _TONE_SIGNALS.items():
        if keyword in segment.source_text:
            return tone

    # 3. Scene mood fallback
    mood = ctx.get("mood", "").lower()
    for keyword, tone in _TONE_SIGNALS.items():
        if keyword in mood:
            return tone

    return "neutral"


# ─────────────────────────────────────────────────────────────────────────────
# Candidate Scorer — rates each candidate against character_voice
# ─────────────────────────────────────────────────────────────────────────────

_TONE_VOCAB: Dict[str, List[str]] = {
    "provocative": ["Orgasmus", "heiß", "schäbig", "geil", "nackt", "begehren", "hungrig", "Sex"],
    "raw":         ["schäbig", "wertlos", "billig", "dreck", "kaputtgemacht", "kaputt", "brutal"],
    "cold":        ["schweigt", "Stille", "leer", "nichts", "gleichgültig", "kalt"],
    "intimate":    ["schweigt", "leise", "zart", "nah", "geflüstert", "berühren"],
    "restrained":  ["vielleicht", "irgendwie", "fast", "kaum", "zurückgehalten"],
    "ironic":      ["natürlich", "klar", "sicher", "toll", "super", "wirklich"],
    "tender":      ["sanft", "warm", "liebevoll", "zärtlich", "vorsichtig"],
    "neutral":     [],
}


def score_candidates(
    candidates: List["TranslationCandidate"],
    target_tone: str,
    character_voice: str = ""
) -> List[float]:
    """
    Score each candidate [0.0, 1.0] based on how well it aligns with the target tone.
    Higher = better fit. Used to guide selection and expose confidence.
    """
    tone_words = set(w.lower() for w in _TONE_VOCAB.get(target_tone, []))

    # Add character voice keywords if provided
    for trait, vocab in _TONE_VOCAB.items():
        if trait in character_voice.lower():
            tone_words.update(w.lower() for w in vocab)

    scores = []
    for cand in candidates:
        text_lower = cand.text.lower()
        if not tone_words:
            scores.append(0.5)
            continue
        hits = sum(1 for w in tone_words if w in text_lower)
        # Penalize over-long lines (suggests over-explanation)
        length_penalty = max(0.0, 1.0 - (len(cand.text) - 60) / 100) if len(cand.text) > 60 else 1.0
        score = min(1.0, hits / max(1, len(tone_words) * 0.3)) * length_penalty
        scores.append(round(score, 3))

    return scores


# ─────────────────────────────────────────────────────────────────────────────
# Smart Line Break — subtitle-aware splitting
# ─────────────────────────────────────────────────────────────────────────────

_BREAK_BEFORE = re.compile(
    r"\b(aber|doch|und|oder|weil|dass|wenn|als|ob|wie|obwohl|during|but|and|because|that|when|while)\b",
    re.IGNORECASE
)


def smart_line_break(text: str, max_chars: int = 42) -> str:
    """
    Break subtitle text at natural language boundaries.
    Priority: conjunctions > commas > midpoint word boundary.
    Returns text unchanged if it fits on one line.
    """
    if len(text) <= max_chars:
        return text

    # Try breaking before a conjunction near the midpoint
    mid = len(text) // 2
    best_pos = None
    best_dist = len(text)

    for m in _BREAK_BEFORE.finditer(text):
        pos = m.start()
        if pos == 0:
            continue
        dist = abs(pos - mid)
        if dist < best_dist and 10 <= pos <= len(text) - 10:
            best_dist = dist
            best_pos = pos

    if best_pos:
        return text[:best_pos].rstrip() + "\n" + text[best_pos:].lstrip()

    # Break at comma near midpoint
    for i in range(mid, len(text)):
        if text[i] in ",;":
            return text[:i + 1].rstrip() + "\n" + text[i + 1:].lstrip()
    for i in range(mid - 1, -1, -1):
        if text[i] in ",;":
            return text[:i + 1].rstrip() + "\n" + text[i + 1:].lstrip()

    # Fall back to word boundary nearest midpoint
    for i in range(mid, len(text)):
        if text[i] == " ":
            return text[:i] + "\n" + text[i + 1:]
    for i in range(mid - 1, -1, -1):
        if text[i] == " ":
            return text[:i] + "\n" + text[i + 1:]

    return text


# ─────────────────────────────────────────────────────────────────────────────
# Emotional Arc Tracker — optional batch-level analysis
# ─────────────────────────────────────────────────────────────────────────────

_TONE_VALENCE: Dict[str, float] = {
    "tender": 0.8,
    "intimate": 0.6,
    "neutral": 0.5,
    "restrained": 0.4,
    "ironic": 0.3,
    "cold": 0.2,
    "provocative": 0.1,
    "raw": 0.0,
}


class EmotionalArcTracker:
    """
    Tracks tone distribution across a processed batch.
    Detects flat arcs, sudden jumps, and drift.
    """

    def __init__(self):
        self._arc: List[Tuple[int, str, float]] = []  # (seg_id, tone, valence)

    def record(self, seg_id: int, tone: str):
        valence = _TONE_VALENCE.get(tone, 0.5)
        self._arc.append((seg_id, tone, valence))

    def summary(self) -> Dict:
        if not self._arc:
            return {}
        tones = [t for _, t, _ in self._arc]
        valences = [v for _, _, v in self._arc]
        tone_counts: Dict[str, int] = {}
        for t in tones:
            tone_counts[t] = tone_counts.get(t, 0) + 1

        # Detect jumps (valence change > 0.4 between adjacent segments)
        jumps = []
        for i in range(1, len(self._arc)):
            delta = abs(self._arc[i][2] - self._arc[i - 1][2])
            if delta >= 0.4:
                jumps.append({
                    "from_id": self._arc[i - 1][0],
                    "to_id": self._arc[i][0],
                    "from_tone": self._arc[i - 1][1],
                    "to_tone": self._arc[i][1],
                    "delta": round(delta, 2)
                })

        # Detect flat arc (same tone > 60% of batch)
        dominant = max(tone_counts, key=tone_counts.get)
        flat = tone_counts[dominant] / len(tones) > 0.6

        return {
            "total_segments": len(self._arc),
            "tone_distribution": tone_counts,
            "dominant_tone": dominant,
            "flat_arc_warning": flat,
            "tone_jumps": jumps,
            "valence_curve": [round(v, 2) for _, _, v in self._arc],
            "mean_valence": round(sum(valences) / len(valences), 2),
        }

    def reset(self):
        self._arc = []


# ─────────────────────────────────────────────────────────────────────────────
# LLM Caller (shared, singleton)
# ─────────────────────────────────────────────────────────────────────────────

class _LLMCaller:
    _anthropic_client = None
    _openai_client = None

    def _anthropic(self):
        if self._anthropic_client is None and ANTHROPIC_AVAILABLE:
            key = os.getenv("ANTHROPIC_API_KEY")
            if key:
                self._anthropic_client = _anthropic_lib.Anthropic(api_key=key)
        return self._anthropic_client

    def _openai(self):
        if self._openai_client is None and OPENAI_AVAILABLE:
            key = os.getenv("OPENAI_API_KEY")
            if key:
                self._openai_client = _OpenAI(api_key=key)
        return self._openai_client

    def call(self, system: str, user: str, max_tokens: int = 1024) -> str:
        client = self._anthropic()
        if client:
            resp = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}]
            )
            return resp.content[0].text

        client = self._openai()
        if client:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                max_tokens=max_tokens
            )
            return resp.choices[0].message.content

        raise RuntimeError("No LLM API available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY.")


_llm = _LLMCaller()


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — Segmentation Agent
# ─────────────────────────────────────────────────────────────────────────────

class SegmentationAgent:
    """
    Normalizes raw SRT or list-of-dict input into SubtitleSegment objects.
    Does NOT translate. Does NOT modify meaning.
    Flags structural issues only.
    """

    @staticmethod
    def parse_srt(srt_text: str, language: str = "zh") -> List[SubtitleSegment]:
        segments = []
        blocks = re.split(r"\n\s*\n", srt_text.strip())
        for block in blocks:
            lines = [l.rstrip() for l in block.strip().split("\n") if l.strip()]
            if len(lines) < 3:
                continue
            try:
                seg_id = int(lines[0].strip())
            except ValueError:
                continue
            tc_match = re.match(
                r"(\d{2}:\d{2}:\d{2}[,:.]\d{2,3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,:.]\d{2,3})",
                lines[1]
            )
            if not tc_match:
                continue
            start, end = tc_match.group(1), tc_match.group(2)
            text = " ".join(lines[2:]).strip()
            segments.append(SubtitleSegment(id=seg_id, start=start, end=end,
                                             source_text=text, language=language))
        return segments

    @staticmethod
    def parse_rows(rows: List[Dict], language: str = "zh") -> List[SubtitleSegment]:
        segments = []
        for i, row in enumerate(rows):
            text = row.get("zh") or row.get("source") or row.get("text") or ""
            segments.append(SubtitleSegment(
                id=int(row.get("id", i + 1)),
                start=str(row.get("start", "00:00:00,000")),
                end=str(row.get("end", "00:00:00,000")),
                source_text=text,
                language=language
            ))
        return segments

    @staticmethod
    def flag_issues(segment: SubtitleSegment) -> List[str]:
        issues = []
        if len(segment.source_text) > 60:
            issues.append(f"Source text long ({len(segment.source_text)} chars)")
        if not segment.source_text.strip():
            issues.append("Empty source text")
        return issues


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — Translation Agent
# ─────────────────────────────────────────────────────────────────────────────

class TranslationAgent:
    """
    Generates exactly 3 translation candidates per segment.
    Does NOT select. Does NOT apply tone rules.
    Receives a context window so it understands surrounding lines.
    """

    SYSTEM = (
        "You are a professional film subtitle translator. "
        "You produce multiple candidates — you do NOT select or judge them. "
        "Respond ONLY with a valid JSON array of exactly 3 strings. "
        "No markdown. No explanation. No extra text."
    )

    def translate(
        self,
        segment: SubtitleSegment,
        target_lang: str,
        mode: str,
        context_window: str = ""
    ) -> List[TranslationCandidate]:
        user = (
            f"Source ({segment.language.upper()}): {segment.source_text}\n"
            f"Target language: {target_lang}\n"
            f"Mode: {mode}\n"
        )
        if context_window:
            user += f"\nSurrounding lines (for context only — translate only the marked line →):\n{context_window}\n"
        user += (
            "\nReturn a JSON array of exactly 3 subtitle candidates. "
            "Vary tone: [neutral, poetic/literary, direct/raw]. "
            "Each must be concise enough for a subtitle."
        )
        raw = _llm.call(self.SYSTEM, user, max_tokens=512)
        return self._parse(raw)

    def _parse(self, raw: str) -> List[TranslationCandidate]:
        try:
            cleaned = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("```")
            data = json.loads(cleaned)
            if isinstance(data, list):
                return [TranslationCandidate(text=str(c)) for c in data[:3]]
        except Exception:
            pass
        found = re.findall(r'"([^"]{3,})"', raw)
        if found:
            return [TranslationCandidate(text=t) for t in found[:3]]
        lines = [l.strip().lstrip("1234567890.-) ") for l in raw.strip().split("\n") if l.strip()]
        return [TranslationCandidate(text=l) for l in lines[:3]] or [TranslationCandidate(text=raw.strip())]


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3 — Tone Calibration Agent
# ─────────────────────────────────────────────────────────────────────────────

class ToneCalibrationAgent:
    """
    This is NOT a translator. This is a director.
    Selects the best candidate based on scene context and character voice.
    Returns (selected_text, tone_tag, rationale).
    """

    SYSTEM = (
        "You are a film dialogue director. Your job is NOT translation — it is direction. "
        "Given multiple translation candidates, select the one that best serves the scene. "
        "Prioritize subtext, character voice, and cinematic intent over literal accuracy. "
        "Respond ONLY with valid JSON. No markdown. No extra text."
    )

    TONE_OPTIONS = ["restrained", "provocative", "ironic", "intimate", "neutral", "raw", "cold", "tender"]

    def calibrate(
        self,
        segment: SubtitleSegment,
        candidates: List[TranslationCandidate],
        scene_context: Optional[Dict],
        memory: Optional["LocalizationMemory"] = None
    ) -> Tuple[str, str, str, float]:
        """
        Returns (selected_text, tone_tag, rationale, confidence_0_to_1).
        inferred_tone from rule-based step is passed to the LLM as a hypothesis.
        """
        ctx = scene_context or {}
        char = ctx.get("character", "unspecified")

        # Pre-LLM: rule-based tone inference
        inferred = infer_tone(segment, scene_context, memory)

        # Pre-LLM: score candidates against inferred tone
        char_voice = (memory.character_voice.get(char, "") if memory else "")
        scores = score_candidates(candidates, inferred, char_voice)

        char_voice_note = ""
        if memory and char in memory.character_voice:
            char_voice_note = f"\nCharacter voice for '{char}': {memory.character_voice[char]}"

        user = (
            f"Source: {segment.source_text}\n"
            f"Candidates:\n" +
            "\n".join(
                f"  {i+1}. {c.text}  [voice_score: {scores[i] if i < len(scores) else 0:.2f}]"
                for i, c in enumerate(candidates)
            ) +
            f"\n\nPre-analysis suggests tone: {inferred}"
            f"\nScene mood: {ctx.get('mood', 'unspecified')}"
            f"\nCharacter: {char}"
            f"\nRelationship: {ctx.get('relationship', 'unspecified')}"
            f"{char_voice_note}"
            f"\n\nTone options: {', '.join(self.TONE_OPTIONS)}"
            '\n\nReturn JSON: '
            '{"selected": "<chosen line>", "tone": "<tone tag>", '
            '"rationale": "<1 sentence>", "confidence": <0.0-1.0>}'
        )
        raw = _llm.call(self.SYSTEM, user, max_tokens=300)
        return self._parse(raw, candidates, scores)

    def _parse(
        self,
        raw: str,
        candidates: List[TranslationCandidate],
        scores: List[float]
    ) -> Tuple[str, str, str, float]:
        try:
            cleaned = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("```")
            data = json.loads(cleaned)
            confidence = float(data.get("confidence", 0.5))
            return (
                data.get("selected", candidates[0].text if candidates else ""),
                data.get("tone", "neutral"),
                data.get("rationale", ""),
                min(1.0, max(0.0, confidence))
            )
        except Exception:
            best_idx = scores.index(max(scores)) if scores else 0
            best = candidates[best_idx].text if candidates else raw.strip()
            return (best, "neutral", "", max(scores) if scores else 0.5)


# ─────────────────────────────────────────────────────────────────────────────
# Stage 4 — Consistency Engine
# ─────────────────────────────────────────────────────────────────────────────

class ConsistencyEngine:
    """
    Enforces memory: phrase locks, character voice, style rules.
    Operates on the selected line AFTER tone calibration.
    Without this stage, tone drift will happen across the film.
    """

    SYSTEM = (
        "You are a film continuity editor. "
        "Enforce locked translations and character voice rules. "
        "Respond ONLY with valid JSON."
    )

    def apply(
        self,
        result: LocalizationResult,
        memory: LocalizationMemory
    ) -> Tuple[str, List[str]]:
        """Returns (final_text, list_of_changes)"""
        if not memory.phrase_lock and not memory.character_voice:
            return result.selected, []

        # Check if any locked phrase source appears in original, and locked target is missing
        locked_violations = []
        for src_phrase, locked_target in memory.phrase_lock.items():
            if src_phrase in result.source_text and locked_target not in result.selected:
                locked_violations.append(f"Phrase lock: '{src_phrase}' → '{locked_target}' not applied")

        user = (
            f"Current line: {result.selected}\n"
            f"Source text: {result.source_text}\n"
            f"Memory state:\n{json.dumps(memory.to_dict(), ensure_ascii=False, indent=2)}\n\n"
            "Apply consistency rules. If the line already conforms, return it unchanged. "
            'Return JSON: {"final": "<line>", "changes": ["<description>" or empty list]}'
        )
        raw = _llm.call(self.SYSTEM, user, max_tokens=256)
        try:
            cleaned = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("```")
            data = json.loads(cleaned)
            changes = data.get("changes", []) + locked_violations
            return data.get("final", result.selected), [c for c in changes if c]
        except Exception:
            return result.selected, locked_violations


# ─────────────────────────────────────────────────────────────────────────────
# Stage 5 — QA / Director Agent
# ─────────────────────────────────────────────────────────────────────────────

class QADirectorAgent:
    """
    Final validation. Technical + artistic checks.
    Flags issues without rewriting unless a suggestion is obvious.
    """

    SYSTEM = (
        "You are a film subtitle QA director. "
        "Check both technical quality and cinematic quality. "
        "Be strict but concise. Respond ONLY with valid JSON."
    )
    MAX_LINE_CHARS = 42
    MAX_CHARS_PER_SEC = 17.0   # Netflix standard for European languages
    MIN_DURATION_SEC = 0.84    # minimum subtitle display time

    @staticmethod
    def _tc_to_seconds(tc: str) -> float:
        """Convert SRT/frame timecode to seconds."""
        m = re.match(r"(\d{2}):(\d{2}):(\d{2})[,.](\d+)", tc)
        if m:
            h, mm, s, sub = m.groups()
            ms = int(sub.ljust(3, "0")[:3])
            return int(h) * 3600 + int(mm) * 60 + int(s) + ms / 1000.0
        # HH:MM:SS:FF fallback
        m = re.match(r"(\d{2}):(\d{2}):(\d{2}):(\d{2})", tc)
        if m:
            h, mm, s, ff = m.groups()
            return int(h) * 3600 + int(mm) * 60 + int(s) + int(ff) / 25.0
        return 0.0

    def check(self, result: LocalizationResult) -> Tuple[str, List[str], str]:
        """Returns (status, issues, suggestion)"""
        fast_issues = []

        # Length check
        if len(result.final) > self.MAX_LINE_CHARS * 2:
            fast_issues.append(f"Too long: {len(result.final)} chars (max ~{self.MAX_LINE_CHARS * 2})")

        # Reading speed check
        dur = self._tc_to_seconds(result.end) - self._tc_to_seconds(result.start)
        if dur > 0:
            chars_per_sec = len(result.final) / dur
            if chars_per_sec > self.MAX_CHARS_PER_SEC:
                fast_issues.append(
                    f"Too fast: {chars_per_sec:.1f} chars/sec (max {self.MAX_CHARS_PER_SEC})"
                )
        if dur > 0 and dur < self.MIN_DURATION_SEC:
            fast_issues.append(f"Duration too short: {dur:.2f}s (min {self.MIN_DURATION_SEC}s)")

        user = (
            f"Subtitle: {result.final}\n"
            f"Source: {result.source_text}\n"
            f"Tone: {result.selected_tone}\n"
            f"Rationale: {result.tone_rationale}\n\n"
            "Check:\n"
            "- Technical: length, readability, line breaks\n"
            "- Artistic: natural phrasing, tone match, no over-cleaning\n"
            '- Warning sign: "nice German" that kills character voice\n\n'
            'Return JSON: {"status": "approved" or "revise", "issues": [], "suggestion": ""}'
        )
        raw = _llm.call(self.SYSTEM, user, max_tokens=256)
        try:
            cleaned = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("```")
            data = json.loads(cleaned)
            all_issues = fast_issues + [i for i in data.get("issues", []) if i]
            status = "revise" if (fast_issues or data.get("status") == "revise") else "approved"
            return status, all_issues, data.get("suggestion", "")
        except Exception:
            status = "revise" if fast_issues else "approved"
            return status, fast_issues, ""


# ─────────────────────────────────────────────────────────────────────────────
# Stage 6 — Output Agent
# ─────────────────────────────────────────────────────────────────────────────

class OutputAgent:
    """
    Converts LocalizationResult list into delivery formats.
    Handles timecode normalization and line splitting.
    """

    @staticmethod
    def _normalize_tc(tc: str) -> str:
        """Normalize any timecode to SRT format HH:MM:SS,mmm"""
        if re.match(r"\d{2}:\d{2}:\d{2},\d{3}", tc):
            return tc
        # HH:MM:SS:FF (frame-based, assume 25fps)
        m = re.match(r"(\d{2}):(\d{2}):(\d{2}):(\d{2})$", tc)
        if m:
            h, mm, s, ff = m.groups()
            ms = int(int(ff) * 1000 / 25)
            return f"{h}:{mm}:{s},{ms:03d}"
        # HH:MM:SS.mmm
        m = re.match(r"(\d{2}):(\d{2}):(\d{2})\.(\d+)", tc)
        if m:
            h, mm, s, sub = m.groups()
            ms = int(sub.ljust(3, "0")[:3])
            return f"{h}:{mm}:{s},{ms:03d}"
        return tc

    @staticmethod
    @staticmethod
    def _split_for_subtitle(text: str, max_chars: int = 42) -> str:
        return smart_line_break(text, max_chars)

    def to_srt(self, results: List[LocalizationResult]) -> str:
        blocks = []
        for idx, r in enumerate(results, 1):
            start = self._normalize_tc(r.start)
            end = self._normalize_tc(r.end)
            text = self._split_for_subtitle(r.final or r.selected or r.source_text)
            blocks.append(f"{idx}\n{start} --> {end}\n{text}")
        return "\n\n".join(blocks)

    def to_csv(self, results: List[LocalizationResult]) -> str:
        rows = ["id,start,end,source,translation,tone,qa_status,qa_issues"]
        for r in results:
            src = r.source_text.replace(",", "，")
            final = (r.final or r.selected or "").replace(",", "，")
            issues = "; ".join(r.qa_issues).replace(",", ";")
            rows.append(f"{r.id},{r.start},{r.end},{src},{final},{r.selected_tone},{r.qa_status},{issues}")
        return "\n".join(rows)

    def to_bilingual_srt(self, results: List[LocalizationResult]) -> str:
        blocks = []
        for idx, r in enumerate(results, 1):
            start = self._normalize_tc(r.start)
            end = self._normalize_tc(r.end)
            blocks.append(f"{idx}\n{start} --> {end}\n{r.source_text}\n{r.final or r.selected}")
        return "\n\n".join(blocks)


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator — wires the pipeline
# ─────────────────────────────────────────────────────────────────────────────

class LocalizationOrchestrator:
    """
    Runs the full 6-stage pipeline.

    Stage order:
      1. (Segmentation — done before calling process_batch)
      2. Translation   — 3 candidates per segment, with context window
      3. Tone          — select best candidate for scene + character
      4. Consistency   — apply memory (phrase locks, character voice)
      5. QA            — validate technical + artistic quality, with revision loop
      6. (Output       — called separately via OutputAgent)
    """

    CONTEXT_WINDOW = 2      # segments before/after to include as context
    QA_MAX_LOOPS = 2        # maximum QA revision iterations per segment

    def __init__(self, memory: Optional[LocalizationMemory] = None, track_arc: bool = False):
        self.memory = memory or LocalizationMemory()
        self.translation = TranslationAgent()
        self.tone = ToneCalibrationAgent()
        self.consistency = ConsistencyEngine()
        self.qa = QADirectorAgent()
        self.output = OutputAgent()
        self.arc = EmotionalArcTracker() if track_arc else None

    def _context_window(self, segments: List[SubtitleSegment], i: int) -> str:
        """Build a text window of ±CONTEXT_WINDOW segments around index i."""
        start = max(0, i - self.CONTEXT_WINDOW)
        end = min(len(segments), i + self.CONTEXT_WINDOW + 1)
        lines = []
        for j in range(start, end):
            marker = "→" if j == i else " "
            lines.append(f"{marker} [{segments[j].id}] {segments[j].source_text}")
        return "\n".join(lines)

    def _qa_revision_loop(self, result: LocalizationResult) -> LocalizationResult:
        """
        If QA flags issues, apply consistency + QA again up to QA_MAX_LOOPS times.
        Stops early if approved or if max iterations reached.
        """
        for iteration in range(self.QA_MAX_LOOPS):
            if result.qa_status == "approved":
                break
            # Re-run consistency with suggestion as context hint
            if result.qa_suggestion:
                result.selected = result.qa_suggestion
            result.final, extra_changes = self.consistency.apply(result, self.memory)
            result.consistency_changes.extend(extra_changes)
            result.qa_status, result.qa_issues, result.qa_suggestion = self.qa.check(result)
            result.qa_iterations = iteration + 1
        return result

    def process_batch(
        self,
        segments: List[SubtitleSegment],
        target_lang: str = "DE",
        translation_mode: str = "cinematic",
        scene_context: Optional[Dict] = None,
        progress_callback=None
    ) -> List[LocalizationResult]:
        """
        Process a batch through all pipeline stages.
        progress_callback(current_int, total_int, LocalizationResult) is called after each segment.
        """
        if self.arc:
            self.arc.reset()

        results: List[LocalizationResult] = []
        total = len(segments)

        for i, seg in enumerate(segments):
            result = LocalizationResult(
                id=seg.id,
                start=seg.start,
                end=seg.end,
                source_text=seg.source_text,
            )

            # Stage 2: Translation — 3 candidates with context window
            ctx_window = self._context_window(segments, i)
            result.candidates = self.translation.translate(
                seg, target_lang, translation_mode, ctx_window
            )

            # Stage 3: Tone calibration — infer_tone → score_candidates → LLM director
            (result.selected, result.selected_tone,
             result.tone_rationale, result.tone_confidence) = self.tone.calibrate(
                seg, result.candidates, scene_context, self.memory
            )
            result.inferred_tone = infer_tone(seg, scene_context, self.memory)
            result.candidate_scores = score_candidates(
                result.candidates, result.selected_tone,
                self.memory.character_voice.get(
                    (scene_context or {}).get("character", ""), ""
                ) if self.memory else ""
            )

            # Stage 4: Consistency — apply memory (phrase locks, character voice)
            result.final, result.consistency_changes = self.consistency.apply(result, self.memory)

            # Stage 5: QA — validate, then loop if flagged
            result.qa_status, result.qa_issues, result.qa_suggestion = self.qa.check(result)
            if result.qa_status == "revise":
                result = self._qa_revision_loop(result)

            # Arc tracking
            if self.arc:
                self.arc.record(result.id, result.selected_tone)

            results.append(result)

            if progress_callback:
                progress_callback(i + 1, total, result)

        return results

    def arc_summary(self) -> Optional[Dict]:
        """Return emotional arc summary if tracking was enabled."""
        return self.arc.summary() if self.arc else None

    def process_srt(self, srt_text: str, language: str = "zh", **kwargs) -> List[LocalizationResult]:
        segments = SegmentationAgent.parse_srt(srt_text, language=language)
        return self.process_batch(segments, **kwargs)
