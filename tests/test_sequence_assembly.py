#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for sequence_assembly.py (V1).

Real ffmpeg calls against tiny synthetic fixture clips generated with
lavfi -- no committed binary test assets, no mocked ffmpeg. Only the
*download* step is mocked (that's the actual network boundary); trimming,
audio synthesis, and concatenation all run the real subprocess pipeline,
so a passing suite means the actual ffmpeg strategy works, not just that
a mock was satisfied.
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sequence_assembly as sa

FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")


def _make_clip(path: Path, duration: float, with_audio: bool, color: str = "blue"):
    args = [FFMPEG, "-y", "-f", "lavfi", "-i", f"color=c={color}:s=64x64:r=10:d={duration}"]
    if with_audio:
        args += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}"]
        args += ["-c:v", "libx264", "-c:a", "aac", "-shortest", str(path)]
    else:
        args += ["-c:v", "libx264", str(path)]
    subprocess.run(args, capture_output=True, check=True)


def _mock_resp(path: Path):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.content = path.read_bytes()
    return resp


@unittest.skipUnless(FFMPEG and FFPROBE, "ffmpeg/ffprobe not available in this environment")
class TestSequenceAssembly(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmpdir.name)
        self.cache_dir = self.tmp / "cache"
        self.clip_with_audio = self.tmp / "with_audio.mp4"
        self.clip_no_audio = self.tmp / "no_audio.mp4"
        _make_clip(self.clip_with_audio, 2.0, with_audio=True, color="blue")
        _make_clip(self.clip_no_audio, 2.0, with_audio=False, color="red")

    def tearDown(self):
        self.tmpdir.cleanup()

    def _take(self, task_id, path, duration=2.0, shot_label_hint=""):
        return sa.SelectedTake(
            provider="minimax", task_id=task_id, source_url=f"https://example/{task_id}.mp4",
            duration_seconds=duration, shot_label_hint=shot_label_hint,
        )

    # ---- materialization / cache ----

    @patch("sequence_assembly.requests.get")
    def test_materialize_downloads_and_caches(self, mock_get):
        mock_get.return_value = _mock_resp(self.clip_with_audio)
        take = self._take("task-a", self.clip_with_audio)
        result = sa.materialize_take(take, "Shot 01", cache_dir=self.cache_dir)
        self.assertTrue(result.exists())
        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(take.cached_path, str(result))

    @patch("sequence_assembly.requests.get")
    def test_materialize_reuses_cache_without_redownloading(self, mock_get):
        mock_get.return_value = _mock_resp(self.clip_with_audio)
        take = self._take("task-b", self.clip_with_audio)
        sa.materialize_take(take, "Shot 01", cache_dir=self.cache_dir)
        sa.materialize_take(take, "Shot 01", cache_dir=self.cache_dir)
        self.assertEqual(mock_get.call_count, 1)  # second call reused the cache

    @patch("sequence_assembly.requests.get")
    def test_missing_source_fails_closed_with_named_shot(self, mock_get):
        mock_get.side_effect = sa.requests.RequestException("boom")
        take = self._take("task-missing", self.clip_with_audio)
        with self.assertRaises(sa.MaterializationError) as ctx:
            sa.materialize_take(take, "Shot 03 — Look Back", cache_dir=self.cache_dir)
        self.assertEqual(ctx.exception.shot_label, "Shot 03 — Look Back")
        self.assertEqual(ctx.exception.task_id, "task-missing")

    def test_empty_source_url_fails_closed(self):
        take = self._take("task-nourl", self.clip_with_audio)
        take.source_url = ""
        with self.assertRaises(sa.MaterializationError):
            sa.materialize_take(take, "Shot 02", cache_dir=self.cache_dir)

    # ---- ordering / trimming / duration ----

    def test_sequence_estimated_duration_sums_trims_in_order(self):
        seq = sa.Sequence(title="T", shots=[
            sa.SequenceShot(shot_label="Shot 01", take=self._take("t1", self.clip_with_audio), in_seconds=0.0, out_seconds=1.0),
            sa.SequenceShot(shot_label="Shot 02", take=self._take("t2", self.clip_no_audio), in_seconds=0.3, out_seconds=1.8),
        ])
        self.assertAlmostEqual(seq.estimated_duration(), 1.0 + 1.5, delta=0.01)
        self.assertEqual([s.shot_label for s in seq.shots], ["Shot 01", "Shot 02"])

    @patch("sequence_assembly.requests.get")
    def test_assemble_two_shots_ordering_and_duration(self, mock_get):
        mock_get.side_effect = [_mock_resp(self.clip_with_audio), _mock_resp(self.clip_no_audio)]
        seq = sa.Sequence(title="T", shots=[
            sa.SequenceShot(shot_label="Shot 01", take=self._take("t1", self.clip_with_audio), out_seconds=1.0),
            sa.SequenceShot(shot_label="Shot 02", take=self._take("t2", self.clip_no_audio), out_seconds=1.5),
        ])
        out = self.tmp / "out.mp4"
        result = sa.assemble_sequence(seq, out, cache_dir=self.cache_dir)
        self.assertTrue(result.exists())

        probe = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(result)],
            capture_output=True, text=True,
        )
        self.assertAlmostEqual(float(probe.stdout.strip()), 2.5, delta=0.3)

    # ---- the specific audio concern: mixed/missing audio must not crash ----

    @patch("sequence_assembly.requests.get")
    def test_clip_without_audio_gets_a_synthesized_silent_track(self, mock_get):
        mock_get.return_value = _mock_resp(self.clip_no_audio)
        seq = sa.Sequence(title="T", shots=[
            sa.SequenceShot(shot_label="Shot 02", take=self._take("t-noaudio", self.clip_no_audio), out_seconds=1.0),
        ])
        out = self.tmp / "out_noaudio.mp4"
        sa.assemble_sequence(seq, out, cache_dir=self.cache_dir)

        probe = subprocess.run(
            [FFPROBE, "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type",
             "-of", "csv=p=0", str(out)],
            capture_output=True, text=True,
        )
        self.assertIn("audio", probe.stdout)

    @patch("sequence_assembly.requests.get")
    def test_mixed_audio_presence_across_clips_does_not_crash(self, mock_get):
        mock_get.side_effect = [_mock_resp(self.clip_with_audio), _mock_resp(self.clip_no_audio)]
        seq = sa.Sequence(title="T", shots=[
            sa.SequenceShot(shot_label="Shot 01", take=self._take("t1b", self.clip_with_audio), out_seconds=1.0),
            sa.SequenceShot(shot_label="Shot 02", take=self._take("t2b", self.clip_no_audio), out_seconds=1.0),
        ])
        out = self.tmp / "out_mixed.mp4"
        result = sa.assemble_sequence(seq, out, cache_dir=self.cache_dir)
        self.assertTrue(result.exists() and result.stat().st_size > 0)

    # ---- take replacement / deliberate label mismatch ----

    def test_deliberate_label_mismatch_is_not_blocked(self):
        """A take generated under one shot label can be placed into a
        different shot slot -- the mismatch is preserved/visible, not
        prevented."""
        take = self._take("t-a", self.clip_with_audio, shot_label_hint="Shot 02")
        shot = sa.SequenceShot(shot_label="Shot 03", take=take)
        self.assertEqual(shot.take.shot_label_hint, "Shot 02")
        self.assertEqual(shot.shot_label, "Shot 03")

    @patch("sequence_assembly.requests.get")
    def test_take_can_be_replaced_between_assemblies(self, mock_get):
        mock_get.side_effect = [_mock_resp(self.clip_with_audio), _mock_resp(self.clip_no_audio)]
        shot = sa.SequenceShot(shot_label="Shot 01", take=self._take("t-old", self.clip_with_audio), out_seconds=1.0)
        seq = sa.Sequence(title="T", shots=[shot])
        sa.assemble_sequence(seq, self.tmp / "v1.mp4", cache_dir=self.cache_dir)

        shot.take = self._take("t-new", self.clip_no_audio)  # replace the take
        sa.assemble_sequence(seq, self.tmp / "v2.mp4", cache_dir=self.cache_dir)

        self.assertTrue((self.tmp / "v1.mp4").exists())
        self.assertTrue((self.tmp / "v2.mp4").exists())
        self.assertEqual(mock_get.call_count, 2)  # each distinct task_id fetched once

    # ---- fail-closed: sequence definition survives a failure untouched ----

    def test_failed_assembly_leaves_sequence_object_untouched_and_produces_no_output(self):
        take = self._take("t-fails", self.clip_with_audio)
        seq = sa.Sequence(title="T", shots=[sa.SequenceShot(shot_label="Shot 01", take=take)])
        before = (seq.title, [(s.shot_label, s.take.task_id) for s in seq.shots])

        with patch("sequence_assembly.requests.get", side_effect=sa.requests.RequestException("down")):
            with self.assertRaises(sa.MaterializationError):
                sa.assemble_sequence(seq, self.tmp / "never.mp4", cache_dir=self.cache_dir)

        after = (seq.title, [(s.shot_label, s.take.task_id) for s in seq.shots])
        self.assertEqual(before, after)
        self.assertFalse((self.tmp / "never.mp4").exists())

    def test_empty_sequence_rejected(self):
        seq = sa.Sequence(title="T", shots=[])
        with self.assertRaises(sa.SequenceAssemblyError):
            sa.assemble_sequence(seq, self.tmp / "empty.mp4", cache_dir=self.cache_dir)


if __name__ == "__main__":
    unittest.main()
