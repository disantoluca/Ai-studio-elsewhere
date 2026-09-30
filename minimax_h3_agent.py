#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Deploy-trigger no-op: forces a fresh Railway build after a stale
# deployment was reactivated ahead of this file's real latest commit.
"""
MiniMax H3 Video Generation Provider
For AI Studio Elsewhere

Implements the verified MiniMax v2 video_generation REST contract directly
(no undocumented fields). Sources:
  - https://platform.minimax.io/docs/guides/video-generation
  - https://platform.minimax.io/docs/api-reference/video-generation-v2-create
  (both fetched 2026-09-29)

Scope (V1, frozen per architecture checkpoint 2026-09-29):
  text-to-video, image-to-video (first/last frame), reference-to-video
  (image/video/audio references). H3-Context-IR and 2K regeneration are
  reserved for V1.1 and are NOT implemented here.

Mirrors the shape of runway_video_agent.py (its own dataclasses, its own
class, its own singleton getter) rather than a shared VideoProvider base
class — see architecture checkpoint 2026-09-29.
"""

import os
import time
import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

try:
    from dotenv import load_dotenv
    for _p in (Path(".env"), Path(__file__).parent / ".env"):
        if _p.exists():
            load_dotenv(_p, override=False)
            break
except ImportError:
    pass

logger = logging.getLogger(__name__)

BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io")
CREATE_PATH = "/v2/video_generation"
QUERY_PATH = "/v2/query/video_generation/{task_id}"

# ── Verified capability tables ──────────────────────────────────────────────

MODELS = ("MiniMax-H3", "MiniMax-H3-Max")

MODEL_RESOLUTIONS: Dict[str, set] = {
    "MiniMax-H3": {"768P", "2K"},
    "MiniMax-H3-Max": {"480P", "768P"},
}

MODEL_DURATION_RANGE: Dict[str, tuple] = {
    "MiniMax-H3": (4, 15),
    "MiniMax-H3-Max": (5, 15),
}

VALID_RATIOS = {"adaptive", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"}

FRAME_ROLES = {"first_frame", "last_frame"}
REFERENCE_ROLES = {"reference_image", "reference_video", "reference_audio"}

MAX_REFERENCE_IMAGES = 9
MAX_REFERENCE_VIDEOS = 3
MAX_REFERENCE_AUDIO = 3
MAX_REFERENCE_TOTAL_FILES = 12
MAX_PROMPT_CHARS = 7000

# Documented: "total request body <= 64 MB; use public URLs for large
# files, avoid Base64." Base64 is supported, not forbidden, but this
# guard fails closed locally before any network call rather than relying
# on the API to reject an oversized combination.
MAX_REQUEST_BODY_BYTES = 64 * 1024 * 1024

TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}
IN_PROGRESS_STATUSES = {"queued", "running"}
KNOWN_STATUSES = TERMINAL_STATUSES | IN_PROGRESS_STATUSES


# ── Errors ───────────────────────────────────────────────────────────────────

class MiniMaxH3Error(Exception):
    """Base class for all MiniMax H3 provider errors."""


class MiniMaxConfigError(MiniMaxH3Error):
    """Raised when the provider is not configured (e.g. missing API key)."""


class MiniMaxValidationError(MiniMaxH3Error):
    """Raised when a request violates the verified H3 capability contract."""

    def __init__(self, issues: List[str]):
        self.issues = issues
        super().__init__("; ".join(issues))


class MiniMaxAPIError(MiniMaxH3Error):
    """Raised when MiniMax returns an HTTP/API-level error."""

    def __init__(self, message: str, http_status: Optional[int] = None):
        self.http_status = http_status
        super().__init__(message)


class MiniMaxTimeoutError(MiniMaxH3Error):
    """Raised when a task does not reach a terminal state within the bound."""


# ── Response-boundary normalization ─────────────────────────────────────────

def _extract_task(payload: Any) -> Dict[str, Any]:
    """Normalize the real Query Task envelope: ``{"task": {...}}``.

    Empirically confirmed against the 2026-09-29 production smoke test —
    the Query Task response nests every field (status,
    content, usage, ...) one level down under a top-level "task" key. The
    Create Task response is NOT wrapped this way (it returns a flat
    ``{"task_id": ...}``, also confirmed by the same smoke test) — only
    Query Task responses go through this helper.

    This is the single place that knows about the envelope, so the polling
    logic itself operates on one canonical task dict. Fails closed: a
    missing or malformed envelope raises rather than being treated as
    "still running", so a broken response can never silently stall the
    bounded polling loop until timeout.
    """
    task = payload.get("task") if isinstance(payload, dict) else None
    if not isinstance(task, dict):
        raise MiniMaxAPIError("Malformed MiniMax query response: missing or invalid 'task' envelope")
    return task


# ── Data model ───────────────────────────────────────────────────────────────

@dataclass
class ContentItem:
    """One entry of the API's multimodal `content[]` array."""
    type: str                      # "text" | "image_url" | "video_url" | "audio_url"
    text: Optional[str] = None
    url: Optional[str] = None      # public URL, mm_file://, or base64 data URI
    role: Optional[str] = None     # first_frame | last_frame | reference_image | reference_video | reference_audio

    def to_api_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"type": self.type}
        if self.type == "text":
            d["text"] = self.text
        else:
            d[self.type] = {"url": self.url}
        if self.role:
            d["role"] = self.role
        return d

    def identifier(self) -> str:
        """Non-sensitive, provenance-safe stand-in for this asset. Never
        stores an inline base64 blob — mirrors the data-URI sanitization
        convention already used in runway_video_ui.py."""
        if self.type == "text":
            return "<text>"
        if self.url and self.url.startswith("data:"):
            return "<inline-data>"
        return self.url or "<missing-url>"


@dataclass
class VideoGenRequest:
    prompt: str
    model: str = "MiniMax-H3"
    resolution: str = "768P"
    duration: int = 4
    ratio: str = "adaptive"
    reference_assets: List[ContentItem] = field(default_factory=list)
    callback_url: Optional[str] = None

    @property
    def mode(self) -> str:
        roles = {c.role for c in self.reference_assets if c.role}
        if roles & FRAME_ROLES:
            return "image_to_video"
        if roles & REFERENCE_ROLES:
            return "reference_to_video"
        return "text_to_video"


@dataclass
class GenerationRecord:
    """Frozen V1 provenance schema — architecture checkpoint 2026-09-29.

    `output_url` is MiniMax's own remote result URL. It is NOT assumed to be
    a durable asset reference (MiniMax URLs may expire) — V1 deliberately
    does not download/persist the asset; that is left for a later phase.
    """
    provider: str
    model: str
    mode: str
    resolution: str
    duration_seconds: int
    ratio: str
    prompt: str
    reference_assets: List[Dict[str, str]]
    task_id: Optional[str] = None
    status: str = "queued"
    estimated_cost_usd: Optional[float] = None
    actual_cost_usd: Optional[float] = None
    output_url: Optional[str] = None
    audio_present: Optional[bool] = None
    error: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    pricing_version: Optional[str] = None

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_safe_dict(self) -> Dict[str, Any]:
        """No field in this schema is ever populated with an API key or
        auth header, so this is always safe to log/display/persist."""
        return asdict(self)


# ── Agent ────────────────────────────────────────────────────────────────────

class MiniMaxH3Agent:
    """MiniMax H3 video generation provider.

    Deliberately its own module/class shape (not a shared VideoProvider
    base class) — see architecture checkpoint 2026-09-29.
    """

    # Bounded, increasing backoff — never a tight loop, capped at 10s.
    DEFAULT_POLL_INTERVALS: tuple = (2, 3, 5, 8, 10, 10, 10, 10, 10, 10)

    # 300s was the original (768P/4s-derived) value and is too short: two
    # real 2K/9s production generations on 2026-09-29 took 324s and 361s
    # server-side and were incorrectly reported as client-side timeouts even
    # though they had succeeded. H3's documented ceiling is 15s at 2K, which
    # scales to well over 300s at the observed rate — 900s gives real margin
    # for the slowest documented case without being unbounded.
    DEFAULT_MAX_WAIT_SECONDS = 900

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY")
        self.available = bool(self.api_key)
        self.generation_history: List[GenerationRecord] = []
        if not self.available:
            logger.warning("⚠️ MiniMax H3 agent initialized without MINIMAX_API_KEY — not available")

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    # ---- validation ---------------------------------------------------------

    def validate_request(self, request: VideoGenRequest) -> List[str]:
        """Return a list of human-readable violations (empty = valid).

        Only checks what's structurally verifiable against the documented
        contract (roles, counts, numeric ranges, enums, prompt length).
        Binary properties of reference files (pixel dimensions, exact codec,
        byte size) are not decoded/pre-validated in V1 — the API's own
        error response is authoritative for those.
        """
        issues: List[str] = []

        if request.model not in MODELS:
            issues.append(f"Unknown model '{request.model}'. Must be one of {MODELS}.")
            return issues  # nothing else is checkable without a valid model

        allowed_res = MODEL_RESOLUTIONS[request.model]
        if request.resolution not in allowed_res:
            issues.append(
                f"{request.model} does not support resolution '{request.resolution}'. "
                f"Allowed: {sorted(allowed_res)}."
            )

        lo, hi = MODEL_DURATION_RANGE[request.model]
        if not (isinstance(request.duration, int) and lo <= request.duration <= hi):
            issues.append(
                f"{request.model} duration must be an integer in [{lo}, {hi}], got {request.duration!r}."
            )

        if request.ratio not in VALID_RATIOS:
            issues.append(f"ratio '{request.ratio}' is not one of {sorted(VALID_RATIOS)}.")

        if not request.prompt or not request.prompt.strip():
            issues.append("A non-empty text prompt is required.")
        elif len(request.prompt) > MAX_PROMPT_CHARS:
            issues.append(f"Prompt exceeds {MAX_PROMPT_CHARS} characters ({len(request.prompt)}).")

        roles = [c.role for c in request.reference_assets if c.role]
        frame_roles = [r for r in roles if r in FRAME_ROLES]
        ref_roles = [r for r in roles if r in REFERENCE_ROLES]
        if frame_roles and ref_roles:
            issues.append(
                "image-to-video (first_frame/last_frame) and reference-to-video "
                "(reference_image/reference_video/reference_audio) are mutually "
                "exclusive per request."
            )

        if roles.count("first_frame") > 1:
            issues.append("At most one first_frame reference is allowed.")
        if roles.count("last_frame") > 1:
            issues.append("At most one last_frame reference is allowed.")

        n_images = roles.count("reference_image")
        if n_images > MAX_REFERENCE_IMAGES:
            issues.append(f"At most {MAX_REFERENCE_IMAGES} reference_image entries allowed, got {n_images}.")

        n_videos = roles.count("reference_video")
        if n_videos > MAX_REFERENCE_VIDEOS:
            issues.append(f"At most {MAX_REFERENCE_VIDEOS} reference_video entries allowed, got {n_videos}.")

        n_audio = roles.count("reference_audio")
        if n_audio > MAX_REFERENCE_AUDIO:
            issues.append(f"At most {MAX_REFERENCE_AUDIO} reference_audio entries allowed, got {n_audio}.")

        n_total_files = len(request.reference_assets)
        if n_total_files > MAX_REFERENCE_TOTAL_FILES:
            issues.append(f"At most {MAX_REFERENCE_TOTAL_FILES} reference files total, got {n_total_files}.")

        for item in request.reference_assets:
            if item.type not in ("image_url", "video_url", "audio_url"):
                issues.append(f"Unsupported reference content type '{item.type}'.")
            elif not item.url:
                issues.append(f"Reference item with role '{item.role}' is missing a url.")

        total_body_bytes = len(request.prompt.encode("utf-8"))
        total_body_bytes += sum(len((c.url or "").encode("utf-8")) for c in request.reference_assets)
        if total_body_bytes > MAX_REQUEST_BODY_BYTES:
            mb = total_body_bytes / (1024 * 1024)
            issues.append(
                f"Estimated request body is {mb:.1f} MB, exceeds MiniMax's documented "
                f"64 MB limit — use a public URL instead of inline base64 for large references."
            )

        return issues

    # ---- generation -----------------------------------------------------------

    def generate_video(
        self,
        request: VideoGenRequest,
        pricing_version: Optional[str] = None,
        estimated_cost_usd: Optional[float] = None,
        max_wait_seconds: Optional[int] = None,
    ) -> GenerationRecord:
        record = GenerationRecord(
            provider="minimax",
            model=request.model,
            mode=request.mode,
            resolution=request.resolution,
            duration_seconds=request.duration,
            ratio=request.ratio,
            prompt=request.prompt,
            reference_assets=[
                {"type": c.type, "role": c.role or "", "identifier": c.identifier()}
                for c in request.reference_assets
            ],
            estimated_cost_usd=estimated_cost_usd,
            pricing_version=pricing_version,
        )

        if not self.available:
            record.status = "failed"
            record.error = "MINIMAX_API_KEY not configured"
            self.generation_history.append(record)
            return record

        issues = self.validate_request(request)
        if issues:
            record.status = "failed"
            record.error = "Validation failed: " + "; ".join(issues)
            self.generation_history.append(record)
            return record

        content = [ContentItem(type="text", text=request.prompt).to_api_dict()]
        content += [c.to_api_dict() for c in request.reference_assets]

        payload: Dict[str, Any] = {
            "model": request.model,
            "content": content,
            "resolution": request.resolution,
            "duration": request.duration,
            "ratio": request.ratio,
        }
        if request.callback_url:
            payload["callback_url"] = request.callback_url

        try:
            resp = requests.post(f"{BASE_URL}{CREATE_PATH}", json=payload, headers=self._headers(), timeout=30)
        except requests.RequestException as e:
            record.status = "failed"
            record.error = f"Request to MiniMax failed: {type(e).__name__}: {e}"
            self.generation_history.append(record)
            return record

        if resp.status_code >= 400:
            record.status = "failed"
            record.error = self._format_api_error(resp)
            self.generation_history.append(record)
            return record

        try:
            task_id = resp.json()["task_id"]
        except (ValueError, KeyError) as e:
            record.status = "failed"
            record.error = f"Unexpected create-task response shape: {e}"
            self.generation_history.append(record)
            return record

        record.task_id = task_id
        record.status = "queued"
        record.updated_at = datetime.now(timezone.utc).isoformat()
        self.generation_history.append(record)

        self._poll_until_terminal(record, max_wait_seconds=max_wait_seconds or self.DEFAULT_MAX_WAIT_SECONDS)
        return record

    def _format_api_error(self, resp: requests.Response) -> str:
        try:
            body = resp.json()
            err = body.get("error", {}) if isinstance(body, dict) else {}
            return f"HTTP {resp.status_code}: {err.get('type', 'unknown')}: {err.get('message', resp.text[:300])}"
        except ValueError:
            return f"HTTP {resp.status_code}: {resp.text[:300]}"

    def _poll_until_terminal(self, record: GenerationRecord, max_wait_seconds: int) -> None:
        """Bounded polling with capped backoff. Always terminates: either a
        terminal API status, or an explicit 'timeout' status — never an
        infinite loop."""
        deadline = time.monotonic() + max_wait_seconds
        attempt = 0

        while True:
            if time.monotonic() >= deadline:
                record.status = "timeout"
                record.error = f"Task {record.task_id} did not reach a terminal state within {max_wait_seconds}s"
                record.updated_at = datetime.now(timezone.utc).isoformat()
                return

            interval = self.DEFAULT_POLL_INTERVALS[min(attempt, len(self.DEFAULT_POLL_INTERVALS) - 1)]
            time.sleep(interval)
            attempt += 1

            try:
                resp = requests.get(
                    f"{BASE_URL}{QUERY_PATH.format(task_id=record.task_id)}",
                    headers=self._headers(),
                    timeout=15,
                )
            except requests.RequestException as e:
                logger.warning(f"⚠️ MiniMax poll error (will retry): {e}")
                continue

            if resp.status_code >= 400:
                record.status = "failed"
                record.error = self._format_api_error(resp)
                record.updated_at = datetime.now(timezone.utc).isoformat()
                return

            try:
                body = resp.json()
            except ValueError:
                logger.warning("⚠️ MiniMax poll returned a non-JSON body (will retry)")
                continue

            try:
                task = _extract_task(body)
            except MiniMaxAPIError as e:
                record.status = "failed"
                record.error = str(e)
                record.updated_at = datetime.now(timezone.utc).isoformat()
                return

            status = task.get("status")
            record.updated_at = datetime.now(timezone.utc).isoformat()

            if status not in KNOWN_STATUSES:
                # Fail closed: a missing/unrecognized status is a contract
                # violation, never silently treated as "still running".
                record.status = "failed"
                record.error = f"MiniMax returned an unrecognized or missing task status: {status!r}"
                return

            if status == "succeeded":
                record.status = "succeeded"
                record.output_url = (task.get("content") or {}).get("url")
                record.actual_cost_usd = self._extract_actual_cost(task)
                return
            if status in ("failed", "cancelled"):
                record.status = status
                record.error = str(task.get("error") or f"Task ended with status '{status}'")
                return
            # queued / running — keep polling
            record.status = status

    def _extract_actual_cost(self, task: Dict[str, Any]) -> Optional[float]:
        """The documented Query Task response has no cost field today. This
        only ever returns a value if a future response shape adds one —
        provenance never fabricates a cost that wasn't actually returned.

        The 2026-09-29 production smoke test showed a
        `usage` object containing `total_tokens`/`prompt_tokens`/
        `completion_tokens` (e.g. 130196 completion tokens for a 4s 768P
        clip). This is an observed, undocumented field — video pricing is
        published as per-second, not per-token — so it is deliberately NOT
        used for cost calculation here. Recorded as an open question, not
        acted on."""
        usage = task.get("usage") or {}
        return usage.get("cost_usd")


# ── Post-hoc audio detection (evidence, not inference) ──────────────────────

def _resolve_ffprobe_bin() -> Optional[str]:
    which = shutil.which("ffprobe")
    if which:
        return which
    try:
        import imageio_ffmpeg
        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        candidate = str(Path(ffmpeg_bin).with_name(Path(ffmpeg_bin).name.replace("ffmpeg", "ffprobe")))
        if Path(candidate).exists():
            return candidate
    except Exception:
        pass
    return None


def detect_audio_stream(media_path_or_url: str, ffprobe_bin: Optional[str] = None, timeout: int = 20) -> Optional[bool]:
    """Best-effort, post-hoc audio detection via ffprobe.

    Returns:
      True  -> an audio stream was positively found
      False -> ffprobe ran successfully and found zero audio streams
      None  -> ffprobe unavailable, failed, or gave an inconclusive result

    This NEVER raises and never turns a successful generation into a failed
    one — see architecture checkpoint 2026-09-29, safeguards #2/#7. Official
    MiniMax API docs do not document generated-audio behavior one way or the
    other for H3 (see the pre-implementation report); this function is the
    only source of truth for `audio_present`, and only once real output
    exists to inspect.

    Empirical note (the 2026-09-29 production smoke test): the
    inspected MiniMax-H3 v2 output was H.264 video + stereo AAC audio
    (32kHz, 2 channels), confirming H3 output CAN carry native audio. This
    does not change the function's behavior — audio_present is still
    established per-generation by inspection, never assumed or hard-coded
    True, since this is one observed sample, not a documented guarantee.
    """
    if not media_path_or_url:
        return None

    binary = ffprobe_bin or _resolve_ffprobe_bin()
    if not binary:
        logger.info("ffprobe not available — audio_present left as None")
        return None

    try:
        proc = subprocess.run(
            [
                binary, "-v", "error",
                "-select_streams", "a",
                "-show_entries", "stream=codec_type",
                "-of", "json",
                media_path_or_url,
            ],
            capture_output=True,
            timeout=timeout,
        )
    except Exception as e:
        logger.warning(f"⚠️ ffprobe audio check failed (non-fatal): {e}")
        return None

    if proc.returncode != 0:
        logger.warning(f"⚠️ ffprobe exited {proc.returncode} (non-fatal): {proc.stderr[:300]!r}")
        return None

    try:
        data = json.loads(proc.stdout or b"{}")
    except ValueError:
        return None

    streams = data.get("streams")
    if streams is None:
        return None
    return len(streams) > 0


# ── Singleton accessor (matches runway_video_agent.get_runway_agent()) ──────

_minimax_h3_agent: Optional[MiniMaxH3Agent] = None


def get_minimax_h3_agent() -> MiniMaxH3Agent:
    """Singleton getter, matching runway_video_agent.get_runway_agent().

    Re-constructs the agent if it was previously built without a key but
    one has since appeared in the environment (e.g. entered into the
    Streamlit sidebar after the tab was first rendered) — otherwise the
    very first unconfigured visit to the tab would permanently freeze
    `available=False` for the life of the server process, since Streamlit
    reruns the script but this module-level singleton persists across
    those reruns. Once truly available, the same instance is kept (so
    `generation_history` isn't lost mid-session)."""
    global _minimax_h3_agent
    if _minimax_h3_agent is None or (not _minimax_h3_agent.available and os.getenv("MINIMAX_API_KEY")):
        _minimax_h3_agent = MiniMaxH3Agent()
    return _minimax_h3_agent
