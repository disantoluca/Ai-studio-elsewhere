"""
Runway ML Video Generation Provider.

Handles AI video generation from fashion images using Runway ML API.

CRITICAL: Requires X-Runway-Version header in all requests.
"""

import logging
import time
from typing import Optional
import requests

from .config import settings

logger = logging.getLogger(__name__)

# ⚠️ Runway API configuration
RUNWAY_API_BASE = "https://api.dev.runwayml.com/v1"
RUNWAY_API_VERSION = "2024-11-06"  # Required by Runway API


class RunwayVideoProvider:
    """
    Video generation provider using Runway ML.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Initialize Runway provider.

        Args:
            api_key: Optional Runway API key.
                     If None, falls back to settings.runway_api_key.
        """
        self.api_key: str = api_key or settings.runway_api_key
        self.enabled: bool = bool(self.api_key)

        # Model name for Runway API
        self.model: str = "gen3-alpha"

        if self.enabled:
            logger.info("✅ Runway provider initialized (real mode)")
            logger.info(f"[Runway] API Base: {RUNWAY_API_BASE}")
            logger.info(f"[Runway] API Version: {RUNWAY_API_VERSION}")
            logger.info(f"[Runway] Model: {self.model}")
        else:
            logger.warning("⚠️ Runway provider initialized (API key not set)")

    # --------------------------------------------------------------------- #
    # Public API used by workers.py
    # --------------------------------------------------------------------- #

    async def generate_video(
        self,
        image_source: str,
        prompt: str,
        duration_seconds: int = 4,
    ) -> str:
        """
        Generate AI video from an image using Runway ML.

        Args:
            image_source: URL of source fashion image (or base64 data URL)
            prompt: Text prompt describing the motion/style
            duration_seconds: Output video length

        Returns:
            URL to the generated video (MP4)

        Raises:
            RuntimeError: If API not enabled or request fails
            TimeoutError: If generation times out
        """
        if not self.enabled:
            raise RuntimeError(
                "Runway provider not enabled. Check RUNWAY_API_KEY environment variable."
            )

        logger.info(f"[Runway] Starting video generation")
        logger.info(f"[Runway] Image: {image_source[:100]}..." if len(image_source) > 100 else f"[Runway] Image: {image_source}")
        logger.info(f"[Runway] Prompt: {prompt[:100]}...")
        logger.info(f"[Runway] Duration: {duration_seconds}s")
        logger.info(f"[Runway] Model: {self.model}")

        try:
            video_url = await self._call_runway_api(
                image_source=image_source,
                prompt=prompt,
                duration_seconds=duration_seconds,
            )
            
            logger.info(f"[Runway] ✅ Successfully generated video")
            logger.info(f"[Runway] Video URL: {video_url}")
            return video_url

        except Exception as runway_error:
            logger.error(f"[Runway] ❌ generate_video failed: {runway_error}", exc_info=True)
            logger.error(f"[Runway] Exception type: {type(runway_error).__name__}")
            # Propagate error - let worker handle fallback to DashScope
            raise

    # --------------------------------------------------------------------- #
    # Internal helper: real Runway API call
    # --------------------------------------------------------------------- #

    async def _call_runway_api(
        self,
        image_source: str,
        prompt: str,
        duration_seconds: int = 4,
    ) -> str:
        """
        Call Runway ML API to generate video.

        Steps:
        1. Create a generation job
        2. Poll job status until completion
        3. Extract and return video URL

        Args:
            image_source: Source image URL (or base64 data URL)
            prompt: Motion/style prompt
            duration_seconds: Video duration

        Returns:
            Video URL from Runway

        Raises:
            RuntimeError: If API errors or response invalid
            TimeoutError: If generation takes too long
        """

        if not self.api_key:
            raise RuntimeError("RUNWAY_API_KEY is not set")

        # ===== CRITICAL: Include X-Runway-Version header =====
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Runway-Version": RUNWAY_API_VERSION,
        }

        # ===== STEP 1: Create generation job =====
        create_url = f"{RUNWAY_API_BASE}/generations"

        payload = {
            "model": self.model,
            "input": {
                "prompt": prompt,
                "image": image_source,
                "duration": duration_seconds,
            },
        }

        logger.info(f"[Runway] POST {create_url}")
        logger.info(f"[Runway] X-Runway-Version: {RUNWAY_API_VERSION}")
        logger.debug(f"[Runway] Payload: {payload}")

        try:
            resp = requests.post(create_url, json=payload, headers=headers, timeout=60)
            logger.info(f"[Runway] Create HTTP {resp.status_code}")
        except requests.exceptions.Timeout:
            logger.error("[Runway] Create request timed out (60s)")
            raise RuntimeError("Runway create request timed out")
        except requests.exceptions.RequestException as e:
            logger.error(f"[Runway] Create request failed: {e}")
            raise RuntimeError(f"Runway create request failed: {e}")

        # Check for HTTP errors
        if resp.status_code != 200:
            logger.error(f"[Runway] HTTP {resp.status_code}: {resp.text}")
            try:
                resp.raise_for_status()
            except requests.exceptions.HTTPError as e:
                logger.error(f"[Runway] HTTP Error: {e}")
                raise RuntimeError(f"Runway API error: HTTP {resp.status_code}")

        # Parse response
        try:
            data = resp.json()
            logger.debug(f"[Runway] Create response: {data}")
        except ValueError as e:
            logger.error(f"[Runway] Invalid JSON response: {e}")
            logger.error(f"[Runway] Response text: {resp.text}")
            raise RuntimeError("Runway response is not valid JSON")

        # Extract job ID from response
        job_id = data.get("id") or data.get("generation_id")
        if not job_id:
            logger.error(f"[Runway] Response missing job ID: {data}")
            raise RuntimeError("Runway response missing job ID")

        logger.info(f"[Runway] Job created: {job_id}")

        # ===== STEP 2: Poll job status until completion =====
        status_url = f"{RUNWAY_API_BASE}/generations/{job_id}"
        max_polls = 120  # ~10 minutes at 5s intervals
        poll_interval = 5  # seconds

        logger.info(f"[Runway] Polling job status (max {max_polls} polls, {poll_interval}s interval)")

        for poll_count in range(max_polls):
            try:
                r = requests.get(status_url, headers=headers, timeout=30)
                logger.debug(f"[Runway] Status poll HTTP {r.status_code}")
            except requests.exceptions.Timeout:
                logger.warning(f"[Runway] Status poll {poll_count} timed out")
                time.sleep(poll_interval)
                continue
            except requests.exceptions.RequestException as e:
                logger.error(f"[Runway] Status poll failed: {e}")
                raise RuntimeError(f"Runway status poll failed: {e}")

            if r.status_code != 200:
                logger.error(f"[Runway] Status HTTP {r.status_code}: {r.text}")
                raise RuntimeError(f"Runway status error: HTTP {r.status_code}")

            try:
                status_data = r.json()
            except ValueError as e:
                logger.error(f"[Runway] Invalid JSON in status response: {e}")
                time.sleep(poll_interval)
                continue

            # Extract status (Runway uses "status" or "state" depending on response type)
            status = status_data.get("status") or status_data.get("state")
            logger.info(f"[Runway] Poll {poll_count}: status={status}")

            # ===== Job completed successfully =====
            if status in ("succeeded", "completed"):
                logger.info(f"[Runway] ✅ Job completed")
                
                # Extract video URL from output
                output = status_data.get("output")
                if output:
                    # Try different URL field names
                    video_url = output.get("url") if isinstance(output, dict) else None
                    if not video_url and isinstance(output, list) and len(output) > 0:
                        video_url = output[0].get("url")
                else:
                    # Fallback: check if URL is at top level
                    video_url = status_data.get("url")

                # Also try the nested structure from Runway docs
                if not video_url:
                    video_url = (
                        output.get("video", {}).get("url")
                        if isinstance(output, dict)
                        else None
                    )

                if not video_url:
                    logger.error(f"[Runway] ❌ No video_url found in response")
                    logger.debug(f"[Runway] Full response: {status_data}")
                    raise RuntimeError("Runway response missing video_url")

                logger.info(f"[Runway] ✅ Video URL: {video_url}")
                return video_url

            # ===== Job failed =====
            if status in ("failed", "error"):
                error_msg = status_data.get("error") or status_data.get("message") or "Unknown error"
                logger.error(f"[Runway] ❌ Job failed: {error_msg}")
                logger.error(f"[Runway] Full response: {status_data}")
                raise RuntimeError(f"Runway job failed: {error_msg}")

            # ===== Still processing - wait and retry =====
            logger.debug(f"[Runway] Job still processing, waiting {poll_interval}s...")
            time.sleep(poll_interval)

        # ===== Timeout =====
        logger.error(f"[Runway] ❌ Job did not complete in {max_polls * poll_interval}s")
        raise TimeoutError(
            f"Runway job {job_id} did not complete within {max_polls * poll_interval}s"
        )

    # --------------------------------------------------------------------- #
    # Status helper
    # --------------------------------------------------------------------- #

    def get_status(self) -> dict:
        """Get provider status for debugging."""
        return {
            "provider": "runway_ml",
            "enabled": self.enabled,
            "mode": "real_api" if self.enabled else "disabled",
            "api_base": RUNWAY_API_BASE,
            "api_version": RUNWAY_API_VERSION,
            "model": self.model,
        }


# ============================================================================
# Singleton factory used by workers / main
# ============================================================================

_provider_instance: Optional[RunwayVideoProvider] = None


def get_runway_provider(api_key: Optional[str] = None) -> RunwayVideoProvider:
    """
    Get or create Runway provider singleton.

    If api_key is not passed, uses settings.runway_api_key from .env.

    Args:
        api_key: Optional API key override

    Returns:
        RunwayVideoProvider singleton instance
    """
    global _provider_instance

    if _provider_instance is None:
        key = api_key or settings.runway_api_key
        _provider_instance = RunwayVideoProvider(api_key=key)

    return _provider_instance
