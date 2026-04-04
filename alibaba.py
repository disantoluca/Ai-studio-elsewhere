"""
Alibaba DashScope Image-to-Video Provider with Base64 Image Support.

Handles video generation from images using Alibaba's DashScope VideoSynthesis API.
Converts images to base64 data URLs to bypass API download restrictions.

CRITICAL: Uses real SDK, no placeholder fallback. If DashScope not available,
raises clear error so worker can understand the issue.
"""

import logging
from typing import Optional, Union
import asyncio
from http import HTTPStatus
import base64

import httpx
from PIL import Image
from io import BytesIO

from .config import settings

logger = logging.getLogger(__name__)

# ===== Import DashScope SDK =====
try:
    from dashscope import VideoSynthesis
    import dashscope
    DASHSCOPE_AVAILABLE = True
    logger.info("✅ DashScope SDK imported successfully")
except ImportError:
    DASHSCOPE_AVAILABLE = False
    logger.error("❌ DashScope SDK not installed. Run: pip install -U dashscope")

# Configure DashScope international endpoint
if DASHSCOPE_AVAILABLE:
    dashscope.base_http_api_url = "https://dashscope-intl.aliyuncs.com/api/v1"
    logger.info("[DashScope] Configured international endpoint")


# ===== Image Processing Helper =====
class ImageProcessor:
    """Convert images to base64 data URLs for API compatibility."""

    MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10MB

    @staticmethod
    def _detect_format(image_data: bytes) -> str:
        """Detect image format from binary data."""
        try:
            with Image.open(BytesIO(image_data)) as img:
                fmt = img.format.lower()
                mime = {
                    "jpeg": "image/jpeg",
                    "png": "image/png",
                    "webp": "image/webp",
                    "gif": "image/gif",
                }.get(fmt, "image/png")
                logger.debug(f"[ImageProcessor] Detected format: {fmt} -> {mime}")
                return mime
        except Exception as e:
            logger.warning(f"[ImageProcessor] Format detection failed: {e}, defaulting to PNG")
            return "image/png"

    @staticmethod
    async def download_image(url: str, timeout: int = 30) -> bytes:
        """Download image from URL with error handling."""
        logger.info(f"[ImageProcessor] Downloading image from: {url}")
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()

                if len(response.content) > ImageProcessor.MAX_SIZE_BYTES:
                    raise RuntimeError(
                        f"Image too large: {len(response.content)} bytes "
                        f"(max: {ImageProcessor.MAX_SIZE_BYTES})"
                    )

                logger.info(f"[ImageProcessor] Downloaded {len(response.content)} bytes")
                return response.content
        except httpx.HTTPError as e:
            logger.error(f"[ImageProcessor] HTTP error: {e}")
            raise RuntimeError(f"Failed to download image: {e}")
        except Exception as e:
            logger.error(f"[ImageProcessor] Unexpected error downloading image: {e}")
            raise RuntimeError(f"Image download failed: {e}")

    @staticmethod
    def bytes_to_base64(image_data: bytes) -> tuple:
        """Convert image bytes to base64 string. Returns (base64_string, mime_type)."""
        base64_str = base64.b64encode(image_data).decode("utf-8")
        mime_type = ImageProcessor._detect_format(image_data)
        logger.debug(f"[ImageProcessor] Encoded {len(image_data)} bytes to base64 ({len(base64_str)} chars)")
        return base64_str, mime_type

    @staticmethod
    async def image_url_to_base64(image_url: str) -> tuple:
        """Download image from URL and convert to base64. Returns (base64_string, mime_type)."""
        image_data = await ImageProcessor.download_image(image_url)
        return ImageProcessor.bytes_to_base64(image_data)

    @staticmethod
    def create_data_url(base64_str: str, mime_type: str = "image/png") -> str:
        """Create a data URL from base64 string."""
        data_url = f"data:{mime_type};base64,{base64_str}"
        logger.debug(f"[ImageProcessor] Created data URL of length {len(data_url)}")
        return data_url

    @staticmethod
    async def process_image_source(image_source: Union[str, bytes]) -> str:
        """
        Process any image source (URL or bytes) into a data URL.
        Main entry point for converting images to API-compatible format.
        """
        logger.info("[ImageProcessor] Processing image source...")
        try:
            if isinstance(image_source, bytes):
                logger.info("[ImageProcessor] Converting bytes to base64...")
                base64_str, mime_type = ImageProcessor.bytes_to_base64(image_source)
            elif isinstance(image_source, str):
                logger.info("[ImageProcessor] Downloading and converting URL...")
                base64_str, mime_type = await ImageProcessor.image_url_to_base64(image_source)
            else:
                raise TypeError(f"Unsupported image source type: {type(image_source)}")

            data_url = ImageProcessor.create_data_url(base64_str, mime_type)
            logger.info(f"[ImageProcessor] ✅ Successfully processed image to data URL")
            return data_url
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"[ImageProcessor] ❌ Failed to process image: {e}")
            raise RuntimeError(f"Image processing failed: {e}")


class AlibabaVideoProvider:
    """
    Video generation provider using Alibaba DashScope with base64 image support.
    
    This is the real implementation - no placeholder fallback.
    Converts images to base64 data URLs to bypass API download restrictions.
    If DashScope is not available or not configured, it raises clear errors.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Initialize Alibaba DashScope provider.

        Args:
            api_key: Optional DashScope API key. If None, uses settings.dashscope_api_key
        """
        self.api_key: str = api_key or settings.dashscope_api_key
        self.enabled: bool = bool(self.api_key) and DASHSCOPE_AVAILABLE

        if self.enabled:
            logger.info("✅ Alibaba DashScope provider initialized (REAL MODE with base64 support)")
            logger.info(f"[DashScope] API key configured: {bool(self.api_key)}")
            logger.info(f"[DashScope] SDK available: {DASHSCOPE_AVAILABLE}")
        else:
            if not DASHSCOPE_AVAILABLE:
                logger.error(
                    "❌ Alibaba DashScope provider NOT enabled: SDK not installed. "
                    "Run: pip install -U dashscope"
                )
            if not self.api_key:
                logger.error(
                    "❌ Alibaba DashScope provider NOT enabled: DASHSCOPE_API_KEY not set. "
                    "Check your .env file."
                )

    # --------------------------------------------------------------------- #
    # Public API used by workers.py - NOW ACCEPTS image_source (URL or bytes)
    # --------------------------------------------------------------------- #

    async def generate_video_from_image(
        self,
        image_source: Union[str, bytes],
        prompt: str,
        duration_seconds: int = 5,
        resolution: str = "720P",
        audio_url: Optional[str] = None,
        model: str = "wan2.5-i2v-preview",
    ) -> str:
        """
        Generate video from image using DashScope VideoSynthesis with base64 handling.

        Args:
            image_source: Either a public image URL (str) or raw image bytes (bytes).
                         Will be converted to base64 data URL automatically.
            prompt: Text description of desired motion
            duration_seconds: Video length in seconds
            resolution: "480P", "720P", or "1080P"
            audio_url: Optional audio URL
            model: DashScope model ID (default: wan2.5-i2v-preview)

        Returns:
            URL to generated video

        Raises:
            RuntimeError: If provider not enabled or API call fails
        """
        if not self.enabled:
            raise RuntimeError(
                "❌ Alibaba DashScope provider is NOT enabled. "
                "Ensure: (1) dashscope SDK installed: pip install -U dashscope, "
                "(2) DASHSCOPE_API_KEY set in .env"
            )

        logger.info(f"[DashScope] Starting video generation")
        logger.info(f"[DashScope] Prompt: {prompt[:100]}...")
        logger.info(f"[DashScope] Duration: {duration_seconds}s, Resolution: {resolution}")
        logger.info(f"[DashScope] Model: {model}")

        try:
            # Step 1: Convert image to base64 data URL
            logger.info("[DashScope] Step 1: Processing image source...")
            try:
                image_data_url = await ImageProcessor.process_image_source(image_source)
                logger.info("[DashScope] ✅ Image converted to base64 data URL")
            except RuntimeError as e:
                logger.error(f"[DashScope] ❌ Image processing failed: {e}")
                raise RuntimeError(f"Failed to process image: {e}") from e

            # Step 2: Call DashScope with base64 data URL
            video_url = await self._call_dashscope_sync(
                image_data_url=image_data_url,
                prompt=prompt,
                duration_seconds=duration_seconds,
                resolution=resolution,
                audio_url=audio_url,
                model=model,
            )

            logger.info(f"[DashScope] ✅ Video generation succeeded")
            logger.info(f"[DashScope] Video URL: {video_url}")
            return video_url

        except Exception as e:
            logger.error(f"[DashScope] ❌ generate_video_from_image failed: {e}", exc_info=True)
            raise

    # --------------------------------------------------------------------- #
    # Internal helper: call DashScope SDK with base64 image
    # --------------------------------------------------------------------- #

    async def _call_dashscope_sync(
        self,
        image_data_url: str,
        prompt: str,
        duration_seconds: int,
        resolution: str,
        audio_url: Optional[str],
        model: str,
    ) -> str:
        """
        Call DashScope VideoSynthesis API with base64 data URL (sync, run in thread).

        Args:
            image_data_url: Base64 data URL (from ImageProcessor)
            prompt: Motion prompt
            duration_seconds: Duration
            resolution: Output resolution
            audio_url: Optional audio
            model: Model ID

        Returns:
            Video URL

        Raises:
            RuntimeError: If API call fails
        """

        def _sync_call():
            """Synchronous DashScope call (runs in thread)."""
            logger.info("[DashScope] Step 2: Calling VideoSynthesis.call()...")
            logger.info(f"  - model: {model}")
            logger.info(f"  - resolution: {resolution}")
            logger.info(f"  - duration: {duration_seconds}s")
            logger.info(f"  - image: data URL (base64)")

            try:
                rsp = VideoSynthesis.call(
                    api_key=self.api_key,
                    model=model,
                    prompt=prompt,
                    img_url=image_data_url,  # Now using base64 data URL
                    audio_url=audio_url,
                    resolution=resolution,
                    duration=duration_seconds,
                    prompt_extend=True,
                    watermark=False,
                    negative_prompt="",
                )

                logger.info(f"[DashScope] Response received")
                logger.debug(f"[DashScope] Raw response: {rsp}")

                return rsp

            except Exception as e:
                logger.error(f"[DashScope] VideoSynthesis.call() failed: {e}", exc_info=True)
                raise

        # Run sync call in thread
        try:
            rsp = await asyncio.to_thread(_sync_call)
        except Exception as e:
            logger.error(f"[DashScope] Async thread call failed: {e}")
            raise RuntimeError(f"DashScope thread execution failed: {e}")

        # ===== Inspect response =====
        logger.info(f"[DashScope] Response status code: {rsp.status_code}")
        logger.info(f"[DashScope] Response code: {rsp.code}")
        logger.info(f"[DashScope] Response message: {rsp.message}")

        # ===== Check HTTP status =====
        if rsp.status_code != HTTPStatus.OK:
            logger.error(
                f"[DashScope] ❌ API returned non-200 status: {rsp.status_code}, "
                f"code={rsp.code}, message={rsp.message}"
            )
            raise RuntimeError(
                f"DashScope API error: HTTP {rsp.status_code}, code={rsp.code}"
            )

        # ===== Extract output object =====
        output = getattr(rsp, "output", None)
        if not output:
            logger.error("[DashScope] ❌ No output object in response")
            logger.debug(f"[DashScope] Full response: {rsp}")
            raise RuntimeError("DashScope returned no output object")

        # ===== Extract fields from output =====
        task_status = getattr(output, "task_status", None)
        video_url = getattr(output, "video_url", None)
        task_id = getattr(output, "task_id", None)
        orig_prompt = getattr(output, "orig_prompt", None)
        actual_prompt = getattr(output, "actual_prompt", None)

        logger.info(f"[DashScope] Task ID: {task_id}")
        logger.info(f"[DashScope] Task Status: {task_status}")
        logger.info(f"[DashScope] Original Prompt: {orig_prompt}")
        logger.info(f"[DashScope] Actual Prompt: {actual_prompt}")
        logger.info(f"[DashScope] Video URL: {video_url}")

        # ===== Validate task success =====
        if task_status != "SUCCEEDED":
            logger.error(f"[DashScope] ❌ Task did not succeed: {task_status}")
            raise RuntimeError(f"DashScope task failed: {task_status}")

        # ===== Validate video URL =====
        if not video_url:
            logger.error("[DashScope] ❌ Empty video_url in response")
            logger.debug(f"[DashScope] Full output: {output}")
            raise RuntimeError("DashScope returned empty video_url")

        logger.info(f"[DashScope] ✅ Video URL is valid and ready")
        return video_url

    # --------------------------------------------------------------------- #
    # Status helper
    # --------------------------------------------------------------------- #

    def get_status(self) -> dict:
        """Get provider status for debugging."""
        return {
            "provider": "alibaba_dashscope",
            "enabled": self.enabled,
            "mode": "real_api_with_base64" if self.enabled else "disabled",
            "sdk_available": DASHSCOPE_AVAILABLE,
            "api_key_set": bool(self.api_key),
        }


# ============================================================================
# Singleton factory
# ============================================================================

_provider_instance: Optional[AlibabaVideoProvider] = None


def get_alibaba_provider(api_key: Optional[str] = None) -> AlibabaVideoProvider:
    """
    Get or create Alibaba DashScope provider singleton.

    Args:
        api_key: Optional API key override

    Returns:
        AlibabaVideoProvider singleton instance
    """
    global _provider_instance

    if _provider_instance is None:
        key = api_key or settings.dashscope_api_key
        _provider_instance = AlibabaVideoProvider(api_key=key)

    return _provider_instance
