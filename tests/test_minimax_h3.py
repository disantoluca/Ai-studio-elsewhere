#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiniMax H3 test island — the first tests in this repository.

Scope is deliberately narrow: minimax_h3_agent.py and minimax_h3_pricing.py
only. No other part of AIStudioElsewhere is exercised, and this suite makes
NO real network call and NO real (paid) MiniMax generation — every HTTP call
and every ffprobe subprocess call is mocked.
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import minimax_h3_agent as mmh3
import minimax_h3_pricing as pricing


def _resp(status_code=200, json_data=None, text=""):
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    r.json.return_value = json_data if json_data is not None else {}
    return r


class TestLifecycleSuccess(unittest.TestCase):
    """create -> queued -> running -> succeeded"""

    @patch("minimax_h3_agent.time.sleep", return_value=None)
    @patch("minimax_h3_agent.requests.get")
    @patch("minimax_h3_agent.requests.post")
    def test_full_success_lifecycle(self, mock_post, mock_get, mock_sleep):
        mock_post.return_value = _resp(200, {"task_id": "task-123"})
        mock_get.side_effect = [
            _resp(200, {"task": {"status": "queued"}}),
            _resp(200, {"task": {"status": "running"}}),
            _resp(200, {"task": {"status": "succeeded", "content": {"url": "https://cdn.minimax.io/out.mp4"}}}),
        ]

        agent = mmh3.MiniMaxH3Agent(api_key="test-key")
        request = mmh3.VideoGenRequest(prompt="a quiet harbor at dawn", model="MiniMax-H3",
                                        resolution="768P", duration=4)
        record = agent.generate_video(request, pricing_version="2026-09-29", estimated_cost_usd=0.32)

        self.assertEqual(record.status, "succeeded")
        self.assertEqual(record.task_id, "task-123")
        self.assertEqual(record.output_url, "https://cdn.minimax.io/out.mp4")
        self.assertEqual(record.mode, "text_to_video")
        self.assertIn(record, agent.generation_history)
        self.assertEqual(mock_get.call_count, 3)


class TestLifecycleFailureModes(unittest.TestCase):

    @patch("minimax_h3_agent.requests.post")
    def test_api_failure_on_create(self, mock_post):
        mock_post.return_value = _resp(401, {"error": {"type": "auth_error", "message": "invalid key"}})
        agent = mmh3.MiniMaxH3Agent(api_key="bad-key")
        request = mmh3.VideoGenRequest(prompt="a scene")
        record = agent.generate_video(request)

        self.assertEqual(record.status, "failed")
        self.assertIn("401", record.error)
        self.assertIn("invalid key", record.error)

    @patch("minimax_h3_agent.time.sleep", return_value=None)
    @patch("minimax_h3_agent.requests.get")
    @patch("minimax_h3_agent.requests.post")
    def test_cancelled_task(self, mock_post, mock_get, mock_sleep):
        mock_post.return_value = _resp(200, {"task_id": "task-999"})
        mock_get.return_value = _resp(200, {"task": {"status": "cancelled", "error": "user cancelled"}})

        agent = mmh3.MiniMaxH3Agent(api_key="test-key")
        record = agent.generate_video(mmh3.VideoGenRequest(prompt="a scene"))

        self.assertEqual(record.status, "cancelled")
        self.assertIn("user cancelled", record.error)

    @patch("minimax_h3_agent.requests.get")
    @patch("minimax_h3_agent.requests.post")
    def test_timeout_never_polls_forever(self, mock_post, mock_get):
        mock_post.return_value = _resp(200, {"task_id": "task-slow"})
        # deadline already in the past -> must resolve to 'timeout' on the very
        # first loop check, without ever calling GET or sleeping.
        agent = mmh3.MiniMaxH3Agent(api_key="test-key")
        record = agent.generate_video(mmh3.VideoGenRequest(prompt="a scene"), max_wait_seconds=-1)

        self.assertEqual(record.status, "timeout")
        self.assertIn("task-slow", record.error)
        mock_get.assert_not_called()

    def test_missing_api_key_never_calls_network(self):
        agent = mmh3.MiniMaxH3Agent(api_key=None)
        self.assertFalse(agent.available)

        with patch("minimax_h3_agent.requests.post") as mock_post:
            record = agent.generate_video(mmh3.VideoGenRequest(prompt="a scene"))
            mock_post.assert_not_called()

        self.assertEqual(record.status, "failed")
        self.assertIn("MINIMAX_API_KEY", record.error)


class TestQueryEnvelopeContract(unittest.TestCase):
    """Regression tests for the real v2 Query Task envelope, {"task": {...}}.

    Root-caused from a real 2026-09-29 smoke test: the client previously read
    status/content off the top level of the response body, which the real
    API never populates there, so every real generation silently ran out the
    polling clock and reported 'timeout' even on server-side success.
    _extract_task() normalizes the envelope in one place; these tests pin
    that behavior down.
    """

    # A sanitized copy of the SHAPE of the payload captured from a real
    # 2026-09-29 smoke test. The task id and output URL below are synthetic
    # (the originals identified a specific paid generation and its asset —
    # neither is a credential, but neither has any testing value either, so
    # they're not reproduced here). Every field name, nesting level, and
    # value type is preserved exactly as observed, including the fields our
    # model doesn't otherwise use (usage.total_tokens etc.).
    REAL_SUCCEEDED_PAYLOAD = {
        "task": {
            "id": "999000111222333",
            "model": "MiniMax-H3",
            "status": "succeeded",
            "created_at": 1790677003,
            "updated_at": 1790677102,
            "content": {
                "url": "https://video-product.cdn.minimax.io/sanitized/output_aigc.mp4"
            },
            "resolution": "768P",
            "duration": 4,
            "usage": {
                "total_seconds": 4,
                "input_seconds": 0,
                "output_seconds": 4,
                "input_image_count": 0,
                "total_tokens": 130196,
                "prompt_tokens": 0,
                "completion_tokens": 130196,
            },
            "ratio": "16:9",
            "task_type": "generation",
        }
    }

    @patch("minimax_h3_agent.time.sleep", return_value=None)
    @patch("minimax_h3_agent.requests.get")
    @patch("minimax_h3_agent.requests.post")
    def test_wrapped_queued_running_succeeded_recognized(self, mock_post, mock_get, mock_sleep):
        mock_post.return_value = _resp(200, {"task_id": "t1"})
        mock_get.side_effect = [
            _resp(200, {"task": {"status": "queued"}}),
            _resp(200, {"task": {"status": "running"}}),
            _resp(200, {"task": {"status": "succeeded", "content": {"url": "https://cdn/out.mp4"}}}),
        ]
        agent = mmh3.MiniMaxH3Agent(api_key="test-key")
        record = agent.generate_video(mmh3.VideoGenRequest(prompt="ok"))

        self.assertEqual(record.status, "succeeded")
        self.assertEqual(record.output_url, "https://cdn/out.mp4")

    @patch("minimax_h3_agent.time.sleep", return_value=None)
    @patch("minimax_h3_agent.requests.get")
    @patch("minimax_h3_agent.requests.post")
    def test_wrapped_failed_recognized(self, mock_post, mock_get, mock_sleep):
        mock_post.return_value = _resp(200, {"task_id": "t2"})
        mock_get.return_value = _resp(200, {"task": {"status": "failed", "error": "content moderation rejected"}})
        agent = mmh3.MiniMaxH3Agent(api_key="test-key")
        record = agent.generate_video(mmh3.VideoGenRequest(prompt="ok"))

        self.assertEqual(record.status, "failed")
        self.assertIn("content moderation rejected", record.error)

    @patch("minimax_h3_agent.time.sleep", return_value=None)
    @patch("minimax_h3_agent.requests.get")
    @patch("minimax_h3_agent.requests.post")
    def test_wrapped_cancelled_recognized(self, mock_post, mock_get, mock_sleep):
        mock_post.return_value = _resp(200, {"task_id": "t3"})
        mock_get.return_value = _resp(200, {"task": {"status": "cancelled"}})
        agent = mmh3.MiniMaxH3Agent(api_key="test-key")
        record = agent.generate_video(mmh3.VideoGenRequest(prompt="ok"))

        self.assertEqual(record.status, "cancelled")

    @patch("minimax_h3_agent.time.sleep", return_value=None)
    @patch("minimax_h3_agent.requests.get")
    @patch("minimax_h3_agent.requests.post")
    def test_missing_task_envelope_fails_closed_not_timeout(self, mock_post, mock_get, mock_sleep):
        """A malformed response (no 'task' key at all) must fail immediately
        with a typed error — it must NOT be silently treated as 'still
        running' and run out the clock."""
        mock_post.return_value = _resp(200, {"task_id": "t4"})
        mock_get.return_value = _resp(200, {"unexpected": "shape"})
        agent = mmh3.MiniMaxH3Agent(api_key="test-key")
        record = agent.generate_video(mmh3.VideoGenRequest(prompt="ok"), max_wait_seconds=300)

        self.assertEqual(record.status, "failed")
        self.assertNotEqual(record.status, "timeout")
        self.assertIn("task", record.error.lower())
        mock_get.assert_called_once()  # fails on the very first poll, no looping

    @patch("minimax_h3_agent.time.sleep", return_value=None)
    @patch("minimax_h3_agent.requests.get")
    @patch("minimax_h3_agent.requests.post")
    def test_missing_status_inside_task_fails_closed(self, mock_post, mock_get, mock_sleep):
        mock_post.return_value = _resp(200, {"task_id": "t5"})
        mock_get.return_value = _resp(200, {"task": {"id": "t5"}})  # no 'status' key
        agent = mmh3.MiniMaxH3Agent(api_key="test-key")
        record = agent.generate_video(mmh3.VideoGenRequest(prompt="ok"), max_wait_seconds=300)

        self.assertEqual(record.status, "failed")
        mock_get.assert_called_once()

    @patch("minimax_h3_agent.time.sleep", return_value=None)
    @patch("minimax_h3_agent.requests.get")
    @patch("minimax_h3_agent.requests.post")
    def test_invalid_status_value_inside_task_fails_closed(self, mock_post, mock_get, mock_sleep):
        mock_post.return_value = _resp(200, {"task_id": "t6"})
        mock_get.return_value = _resp(200, {"task": {"status": "not_a_real_status"}})
        agent = mmh3.MiniMaxH3Agent(api_key="test-key")
        record = agent.generate_video(mmh3.VideoGenRequest(prompt="ok"), max_wait_seconds=300)

        self.assertEqual(record.status, "failed")
        mock_get.assert_called_once()

    def test_extract_task_raises_on_missing_envelope(self):
        with self.assertRaises(mmh3.MiniMaxAPIError):
            mmh3._extract_task({"no": "task key here"})
        with self.assertRaises(mmh3.MiniMaxAPIError):
            mmh3._extract_task({"task": "not-a-dict"})
        with self.assertRaises(mmh3.MiniMaxAPIError):
            mmh3._extract_task(None)

    def test_extract_task_returns_inner_dict_on_valid_envelope(self):
        task = mmh3._extract_task({"task": {"status": "succeeded"}})
        self.assertEqual(task, {"status": "succeeded"})

    @patch("minimax_h3_agent.time.sleep", return_value=None)
    @patch("minimax_h3_agent.requests.get")
    @patch("minimax_h3_agent.requests.post")
    def test_repaired_parser_ingests_the_real_captured_payload(self, mock_post, mock_get, mock_sleep):
        """Replays the sanitized-shape payload from a real 2026-09-29 smoke
        test through the repaired parser (see REAL_SUCCEEDED_PAYLOAD)."""
        mock_post.return_value = _resp(200, {"task_id": "999000111222333"})
        mock_get.return_value = _resp(200, self.REAL_SUCCEEDED_PAYLOAD)

        agent = mmh3.MiniMaxH3Agent(api_key="test-key")
        request = mmh3.VideoGenRequest(prompt="a quiet European street at blue hour",
                                        model="MiniMax-H3", resolution="768P", duration=4, ratio="16:9")
        record = agent.generate_video(request, pricing_version="2026-09-29", estimated_cost_usd=0.32)

        self.assertEqual(record.status, "succeeded")
        self.assertEqual(record.task_id, "999000111222333")
        self.assertTrue(record.output_url.endswith("output_aigc.mp4"))
        # usage.total_tokens is present in the real payload but must NOT
        # surface as actual_cost_usd — no cost field exists in this payload.
        self.assertIsNone(record.actual_cost_usd)

    def test_credentials_absent_from_envelope_errors(self):
        """The typed envelope error must never echo back request headers or
        the API key, even though it's constructed from live-looking data."""
        agent = mmh3.MiniMaxH3Agent(api_key="sk-should-never-appear")
        try:
            mmh3._extract_task({"unexpected": "shape", "Authorization": f"Bearer {agent.api_key}"})
            self.fail("expected MiniMaxAPIError")
        except mmh3.MiniMaxAPIError as e:
            self.assertNotIn("sk-should-never-appear", str(e))


class TestCapabilityValidation(unittest.TestCase):

    def setUp(self):
        self.agent = mmh3.MiniMaxH3Agent(api_key="test-key")

    def test_valid_request_has_no_issues(self):
        req = mmh3.VideoGenRequest(prompt="ok", model="MiniMax-H3", resolution="768P", duration=6)
        self.assertEqual(self.agent.validate_request(req), [])

    def test_unknown_model_rejected(self):
        req = mmh3.VideoGenRequest(prompt="ok", model="MiniMax-Nope")
        issues = self.agent.validate_request(req)
        self.assertTrue(any("Unknown model" in i for i in issues))

    def test_resolution_invalid_for_model(self):
        req = mmh3.VideoGenRequest(prompt="ok", model="MiniMax-H3", resolution="480P", duration=4)
        issues = self.agent.validate_request(req)
        self.assertTrue(any("resolution" in i for i in issues))

    def test_duration_below_model_minimum(self):
        req = mmh3.VideoGenRequest(prompt="ok", model="MiniMax-H3-Max", resolution="768P", duration=4)
        issues = self.agent.validate_request(req)
        self.assertTrue(any("duration" in i for i in issues))

    def test_frame_and_reference_roles_mutually_exclusive(self):
        req = mmh3.VideoGenRequest(
            prompt="ok",
            reference_assets=[
                mmh3.ContentItem(type="image_url", url="https://x/a.png", role="first_frame"),
                mmh3.ContentItem(type="image_url", url="https://x/b.png", role="reference_image"),
            ],
        )
        issues = self.agent.validate_request(req)
        self.assertTrue(any("mutually exclusive" in i for i in issues))

    def test_too_many_reference_images_rejected(self):
        assets = [mmh3.ContentItem(type="image_url", url=f"https://x/{i}.png", role="reference_image")
                  for i in range(10)]
        req = mmh3.VideoGenRequest(prompt="ok", reference_assets=assets)
        issues = self.agent.validate_request(req)
        self.assertTrue(any("reference_image" in i for i in issues))

    def test_empty_prompt_rejected(self):
        req = mmh3.VideoGenRequest(prompt="   ")
        issues = self.agent.validate_request(req)
        self.assertTrue(any("prompt" in i.lower() for i in issues))

    def test_prompt_too_long_rejected(self):
        req = mmh3.VideoGenRequest(prompt="x" * 7001)
        issues = self.agent.validate_request(req)
        self.assertTrue(any("exceeds" in i for i in issues))

    @patch("minimax_h3_agent.requests.post")
    def test_invalid_request_never_reaches_network(self, mock_post):
        req = mmh3.VideoGenRequest(prompt="ok", model="MiniMax-H3", resolution="480P", duration=4)
        record = self.agent.generate_video(req)
        mock_post.assert_not_called()
        self.assertEqual(record.status, "failed")
        self.assertIn("Validation failed", record.error)


class TestPricing(unittest.TestCase):

    def test_h3_output_rates(self):
        self.assertAlmostEqual(pricing.estimate_video_cost("MiniMax-H3", "768P", 4).total_usd, 0.32)
        self.assertAlmostEqual(pricing.estimate_video_cost("MiniMax-H3", "2K", 4).total_usd, 0.52)

    def test_h3_max_output_rates(self):
        self.assertAlmostEqual(pricing.estimate_video_cost("MiniMax-H3-Max", "480P", 5).total_usd, 0.25)
        self.assertAlmostEqual(pricing.estimate_video_cost("MiniMax-H3-Max", "768P", 5).total_usd, 0.40)

    def test_unknown_model_or_resolution_raises(self):
        with self.assertRaises(pricing.MiniMaxPricingError):
            pricing.estimate_video_cost("Not-A-Model", "768P", 4)
        with self.assertRaises(pricing.MiniMaxPricingError):
            pricing.estimate_video_cost("MiniMax-H3", "480P", 4)  # not a valid H3 output resolution

    def test_h3_free_image_threshold(self):
        at_free_limit = pricing.estimate_video_cost("MiniMax-H3", "768P", 4, num_reference_images=5)
        one_over = pricing.estimate_video_cost("MiniMax-H3", "768P", 4, num_reference_images=6)
        self.assertAlmostEqual(at_free_limit.total_usd, 0.32)          # no extra-image line item
        self.assertAlmostEqual(one_over.total_usd, 0.32 + 0.04)        # exactly one billable image

    def test_h3_max_free_image_threshold(self):
        at_free_limit = pricing.estimate_video_cost("MiniMax-H3-Max", "768P", 5, num_reference_images=2)
        one_over = pricing.estimate_video_cost("MiniMax-H3-Max", "768P", 5, num_reference_images=3)
        self.assertAlmostEqual(at_free_limit.total_usd, 0.40)
        self.assertAlmostEqual(one_over.total_usd, 0.40 + 0.074)

    def test_reference_video_cost_by_own_resolution(self):
        est = pricing.estimate_video_cost(
            "MiniMax-H3", "768P", 4, reference_video_seconds=3, reference_video_resolution="2K"
        )
        self.assertAlmostEqual(est.total_usd, 0.32 + (0.13 * 3))

    def test_pricing_version_is_stamped(self):
        est = pricing.estimate_video_cost("MiniMax-H3", "768P", 4)
        self.assertEqual(est.pricing_version, pricing.PRICING_VERSION)
        self.assertEqual(est.pricing_source, pricing.PRICING_SOURCE)


class TestSecretNonLeakage(unittest.TestCase):

    SECRET = "sk-super-secret-do-not-leak"

    def test_secret_absent_from_failed_record(self):
        agent = mmh3.MiniMaxH3Agent(api_key=self.SECRET)
        with patch("minimax_h3_agent.requests.post") as mock_post:
            mock_post.return_value = _resp(401, {"error": {"type": "auth_error", "message": "denied"}})
            record = agent.generate_video(mmh3.VideoGenRequest(prompt="ok"))

        self._assert_no_secret(record)

    @patch("minimax_h3_agent.time.sleep", return_value=None)
    def test_secret_absent_from_succeeded_record(self, mock_sleep):
        agent = mmh3.MiniMaxH3Agent(api_key=self.SECRET)
        with patch("minimax_h3_agent.requests.post") as mock_post, \
             patch("minimax_h3_agent.requests.get") as mock_get:
            mock_post.return_value = _resp(200, {"task_id": "t1"})
            mock_get.return_value = _resp(200, {"task": {"status": "succeeded", "content": {"url": "https://cdn/out.mp4"}}})
            record = agent.generate_video(mmh3.VideoGenRequest(prompt="ok"))

        self._assert_no_secret(record)

    def _assert_no_secret(self, record):
        self.assertNotIn(self.SECRET, str(record))
        self.assertNotIn(self.SECRET, repr(record))
        safe = record.to_safe_dict()
        self.assertNotIn(self.SECRET, json.dumps(safe))
        for value in safe.values():
            self.assertNotEqual(value, self.SECRET)


class TestAudioDetection(unittest.TestCase):

    def _ffprobe_result(self, returncode=0, stdout=b"{}", stderr=b""):
        p = MagicMock()
        p.returncode = returncode
        p.stdout = stdout
        p.stderr = stderr
        return p

    @patch("minimax_h3_agent._resolve_ffprobe_bin", return_value="/usr/bin/ffprobe")
    @patch("minimax_h3_agent.subprocess.run")
    def test_audio_true_when_stream_present(self, mock_run, mock_resolve):
        mock_run.return_value = self._ffprobe_result(
            0, json.dumps({"streams": [{"codec_type": "audio"}]}).encode()
        )
        self.assertTrue(mmh3.detect_audio_stream("https://cdn/out.mp4"))

    @patch("minimax_h3_agent._resolve_ffprobe_bin", return_value="/usr/bin/ffprobe")
    @patch("minimax_h3_agent.subprocess.run")
    def test_audio_false_when_no_stream(self, mock_run, mock_resolve):
        mock_run.return_value = self._ffprobe_result(0, json.dumps({"streams": []}).encode())
        self.assertFalse(mmh3.detect_audio_stream("https://cdn/out.mp4"))

    @patch("minimax_h3_agent._resolve_ffprobe_bin", return_value=None)
    def test_audio_none_when_ffprobe_missing(self, mock_resolve):
        self.assertIsNone(mmh3.detect_audio_stream("https://cdn/out.mp4"))

    @patch("minimax_h3_agent._resolve_ffprobe_bin", return_value="/usr/bin/ffprobe")
    @patch("minimax_h3_agent.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ffprobe", timeout=20))
    def test_audio_none_when_ffprobe_raises(self, mock_run, mock_resolve):
        self.assertIsNone(mmh3.detect_audio_stream("https://cdn/out.mp4"))

    @patch("minimax_h3_agent._resolve_ffprobe_bin", return_value="/usr/bin/ffprobe")
    @patch("minimax_h3_agent.subprocess.run")
    def test_audio_none_when_ffprobe_nonzero_exit(self, mock_run, mock_resolve):
        mock_run.return_value = self._ffprobe_result(1, b"", b"no such file")
        self.assertIsNone(mmh3.detect_audio_stream("https://cdn/out.mp4"))

    @patch("minimax_h3_agent._resolve_ffprobe_bin", return_value="/usr/bin/ffprobe")
    @patch("minimax_h3_agent.subprocess.run", side_effect=OSError("boom"))
    def test_ffprobe_failure_does_not_fail_generation(self, mock_run, mock_resolve):
        """A successful GenerationRecord must stay 'succeeded' even if the
        post-hoc audio probe blows up — this is the exact scenario the
        architecture checkpoint (2026-09-29, safeguards #2/#7) calls out."""
        record = mmh3.GenerationRecord(
            provider="minimax", model="MiniMax-H3", mode="text_to_video",
            resolution="768P", duration_seconds=4, ratio="adaptive",
            prompt="ok", reference_assets=[], status="succeeded",
            output_url="https://cdn/out.mp4",
        )
        record.audio_present = mmh3.detect_audio_stream(record.output_url)

        self.assertEqual(record.status, "succeeded")
        self.assertIsNone(record.audio_present)


if __name__ == "__main__":
    unittest.main()
