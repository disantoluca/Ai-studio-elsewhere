#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sequence Assembly V1 — provider-neutral.

Consumes already-generated, immutable provider records (MiniMax
GenerationRecord today, potentially a Runway equivalent later) via the
small SelectedTake shape below. This module never imports
minimax_h3_agent.py or runway_video_agent.py, and never mutates whatever
provider record a SelectedTake was built from — the adapter that reads a
GenerationRecord into a SelectedTake lives in the UI glue code
(minimax_h3_ui.py), not here. That is what keeps this module genuinely
provider-neutral without inventing a shared VideoProvider abstraction.

V1 scope: ordered selected takes, per-shot in/out trims, hard cuts only,
source audio preserved (a silent track is synthesized only when a source
clip genuinely has none, so concatenation never breaks on a mismatched
stream count across clips), inline preview, duration calculation, MP4
export. No dissolves, titles, music, color grading, multitrack editing,
automatic take selection, or general NLE functionality.

Persistence: materializing a take downloads it once into a local cache
keyed by the immutable task_id. This cache is exactly as durable as
DATA_DIR already is — it does NOT survive a Railway container
replacement any more than project JSON does. That is a known, accepted
V1 limitation, not something this module solves. See architecture
checkpoint 2026-09-30.
"""

import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)

CACHE_DIR = Path(os.getenv("DATA_DIR", "./data")) / "videos"


class SequenceAssemblyError(Exception):
    """Base class for all sequence-assembly errors."""


class MaterializationError(SequenceAssemblyError):
    """Raised when a selected take's source video cannot be fetched/cached.
    Carries the shot_label and task_id so the caller can report exactly
    which shot/take failed — the fail-closed requirement: never assemble a
    sequence silently missing a shot."""

    def __init__(self, shot_label: str, task_id: str, reason: str):
        self.shot_label = shot_label
        self.task_id = task_id
        self.reason = reason
        super().__init__(f"Shot '{shot_label}' (task {task_id}): {reason}")


@dataclass
class SelectedTake:
    """Provider-neutral pointer to one already-generated video. Built by a
    small per-provider adapter (in the UI layer) from an immutable
    provider record — this dataclass never mutates that record; it only
    copies a few fields off it once."""
    provider: str
    task_id: str
    source_url: str
    duration_seconds: float
    shot_label_hint: str = ""      # the label it was generated under, if any
    audio_present: Optional[bool] = None
    cached_path: Optional[str] = None


@dataclass
class SequenceShot:
    shot_label: str
    take: SelectedTake
    in_seconds: float = 0.0
    out_seconds: Optional[float] = None    # None = full source duration

    def effective_out(self) -> float:
        return self.out_seconds if self.out_seconds is not None else self.take.duration_seconds

    def trimmed_duration(self) -> float:
        return max(0.0, self.effective_out() - self.in_seconds)


@dataclass
class Sequence:
    title: str
    shots: List[SequenceShot] = field(default_factory=list)

    def estimated_duration(self) -> float:
        return sum(s.trimmed_duration() for s in self.shots)


def _ffprobe_bin() -> Optional[str]:
    return shutil.which("ffprobe")


def _ffmpeg_bin() -> Optional[str]:
    which = shutil.which("ffmpeg")
    if which:
        return which
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def probe_has_audio(local_path: Path) -> bool:
    """Best-effort local check on an already-materialized file. Unknown or
    failed probes default to False — the safer assumption when building
    the ffmpeg command, since assuming audio that isn't there is exactly
    what makes concatenation fail mysteriously."""
    binary = _ffprobe_bin()
    if not binary:
        return False
    try:
        proc = subprocess.run(
            [binary, "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(local_path)],
            capture_output=True, timeout=20, text=True,
        )
    except Exception:
        return False
    if proc.returncode != 0:
        return False
    return bool(proc.stdout.strip())


def materialize_take(take: SelectedTake, shot_label: str, cache_dir: Optional[Path] = None) -> Path:
    """Download+cache a take's source video once, keyed by its immutable
    task_id. Reuses the cached file on subsequent calls — never
    re-downloads. Always raises MaterializationError (never a bare
    exception) on failure, naming the shot/take explicitly."""
    cache_dir = cache_dir or CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    dest = cache_dir / f"{take.task_id}.mp4"

    if dest.exists() and dest.stat().st_size > 0:
        take.cached_path = str(dest)
        return dest

    if not take.source_url:
        raise MaterializationError(shot_label, take.task_id, "no source URL on this take")

    try:
        resp = requests.get(take.source_url, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise MaterializationError(shot_label, take.task_id, f"download failed: {e}")

    if not resp.content:
        raise MaterializationError(shot_label, take.task_id, "download returned no data")

    tmp = dest.with_suffix(".tmp")
    tmp.write_bytes(resp.content)
    tmp.rename(dest)
    take.cached_path = str(dest)
    return dest


def _probe_duration(path: Path) -> float:
    binary = _ffprobe_bin()
    if not binary:
        return 0.0
    try:
        proc = subprocess.run(
            [binary, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, timeout=20, text=True,
        )
        return float(proc.stdout.strip())
    except Exception:
        return 0.0


def register_local_file(raw_bytes: bytes, cache_dir: Optional[Path] = None) -> SelectedTake:
    """Build a SelectedTake directly from local file bytes (e.g. a
    Streamlit upload), bypassing the download step entirely. Recovers a
    previously-generated clip that's no longer in any provider's in-memory
    generation history -- agent.generation_history is process-memory-only
    and does not survive a Railway redeploy (architecture checkpoint
    2026-09-30). Written into the exact same cache location convention as
    a downloaded take, keyed by a fresh synthetic task_id, so everything
    downstream (materialize_take's cache-hit path, trim, concat) treats it
    identically to a provider-sourced take -- no special-casing needed."""
    cache_dir = cache_dir or CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    task_id = f"local-{uuid.uuid4().hex}"
    dest = cache_dir / f"{task_id}.mp4"
    dest.write_bytes(raw_bytes)

    return SelectedTake(
        provider="local_upload",
        task_id=task_id,
        source_url="",
        duration_seconds=_probe_duration(dest),
        shot_label_hint="",
        audio_present=probe_has_audio(dest),
        cached_path=str(dest),
    )


def _run_ffmpeg(args: List[str]) -> None:
    binary = _ffmpeg_bin()
    if not binary:
        raise SequenceAssemblyError("ffmpeg is not available in this environment")
    proc = subprocess.run([binary, "-y", *args], capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise SequenceAssemblyError(f"ffmpeg failed: {proc.stderr[-2000:]}")


def _normalize_shot_clip(shot: SequenceShot, source_path: Path, out_path: Path) -> None:
    """Trim to [in, out] and re-encode to a uniform codec, always producing
    a clip with both a video AND an audio track — real audio if the source
    has it, a synthesized silent track matching the trimmed duration
    otherwise. This is what lets the final concat pass be a simple,
    reliable stream-copy regardless of which source clips originally had
    audio and which didn't."""
    has_audio = probe_has_audio(source_path)
    duration = shot.trimmed_duration()
    in_s = shot.in_seconds

    if has_audio:
        _run_ffmpeg([
            "-ss", str(in_s), "-i", str(source_path),
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac",
            "-movflags", "+faststart", str(out_path),
        ])
    else:
        _run_ffmpeg([
            "-ss", str(in_s), "-i", str(source_path),
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t", str(duration),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac",
            "-shortest", "-movflags", "+faststart", str(out_path),
        ])


def assemble_sequence(sequence: Sequence, output_path: Path, cache_dir: Optional[Path] = None) -> Path:
    """Fail-closed: materializes every shot's take FIRST; if any shot
    fails, raises MaterializationError naming exactly which one, before any
    ffmpeg work happens, and without mutating `sequence` at all. Only
    assembles once every shot's source is confirmed present locally."""
    if not sequence.shots:
        raise SequenceAssemblyError("Sequence has no shots to assemble")

    cache_dir = cache_dir or CACHE_DIR
    source_paths: List[Path] = [
        materialize_take(shot.take, shot.shot_label, cache_dir) for shot in sequence.shots
    ]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        normalized: List[Path] = []
        for i, (shot, src) in enumerate(zip(sequence.shots, source_paths)):
            clip_out = tmp_path / f"clip_{i:03d}.mp4"
            _normalize_shot_clip(shot, src, clip_out)
            normalized.append(clip_out)

        list_file = tmp_path / "concat_list.txt"
        list_file.write_text("".join(f"file '{p}'\n" for p in normalized))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        _run_ffmpeg([
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c", "copy", "-movflags", "+faststart", str(output_path),
        ])

    return output_path
