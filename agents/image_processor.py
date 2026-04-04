"""
Image processing utilities for converting images to base64 format.
Handles URL downloads, format detection, and data URL generation.
"""

import base64
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional, Union

import httpx
from PIL import Image

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Handle image downloads and base64 encoding for API compatibility."""

    # Maximum file size: 10MB
    MAX_SIZE_BYTES = 10 * 1024 * 1024

    # Supported MIME types
    SUPPORTED_FORMATS = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }

    @staticmethod
    def _detect_format(image_data: bytes) -> str:
        """
        Detect image format from binary data.
        Falls back to PNG if detection fails.
        """
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
        """
        Download image from URL with error handling.

        Args:
            url: Image URL (must be publicly accessible)
            timeout: Request timeout in seconds

        Returns:
            Image binary data

        Raises:
            RuntimeError: If download fails or file too large
        """
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
    def bytes_to_base64(image_data: bytes) -> tuple[str, str]:
        """
        Convert image bytes to base64 string.

        Args:
            image_data: Binary image data

        Returns:
            Tuple of (base64_string, mime_type)
        """
        base64_str = base64.b64encode(image_data).decode("utf-8")
        mime_type = ImageProcessor._detect_format(image_data)

        logger.debug(
            f"[ImageProcessor] Encoded {len(image_data)} bytes to base64 "
            f"({len(base64_str)} chars, mime: {mime_type})"
        )

        return base64_str, mime_type

    @staticmethod
    async def image_url_to_base64(image_url: str) -> tuple[str, str]:
        """
        Download image from URL and convert to base64 with mime type.

        Args:
            image_url: Public image URL

        Returns:
            Tuple of (base64_string, mime_type)

        Raises:
            RuntimeError: If download or encoding fails
        """
        image_data = await ImageProcessor.download_image(image_url)
        return ImageProcessor.bytes_to_base64(image_data)

    @staticmethod
    def create_data_url(base64_str: str, mime_type: str = "image/png") -> str:
        """
        Create a data URL from base64 string.

        Args:
            base64_str: Base64-encoded image data
            mime_type: MIME type of the image

        Returns:
            Data URL string (data:image/png;base64,...)
        """
        data_url = f"data:{mime_type};base64,{base64_str}"
        logger.debug(f"[ImageProcessor] Created data URL of length {len(data_url)}")
        return data_url

    @staticmethod
    async def process_image_source(
        image_source: Union[str, bytes],
    ) -> str:
        """
        Process any image source (URL or bytes) into a data URL.

        This is the main entry point for converting images to API-compatible format.

        Args:
            image_source: Either a public URL string or raw image bytes

        Returns:
            Data URL ready for API consumption

        Raises:
            RuntimeError: If processing fails
        """
        logger.info("[ImageProcessor] Processing image source...")

        try:
            if isinstance(image_source, bytes):
                logger.info("[ImageProcessor] Converting bytes to base64...")
                base64_str, mime_type = ImageProcessor.bytes_to_base64(image_source)
            elif isinstance(image_source, str):
                logger.info("[ImageProcessor] Downloading and converting URL...")
                base64_str, mime_type = await ImageProcessor.image_url_to_base64(
                    image_source
                )
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
