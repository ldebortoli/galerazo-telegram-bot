from __future__ import annotations

import asyncio
import base64
import io
import logging
from collections.abc import Sequence

import av
import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

from .roles import TriggerModerationResult


logger = logging.getLogger(__name__)
MODERATIONS_URL = "https://api.openai.com/v1/moderations"
MODERATION_MODEL = "omni-moderation-latest"
VIDEO_FRAME_FRACTIONS = (0.2, 0.4, 0.6, 0.8)
MAX_IMAGE_DIMENSION = 2048


class OpenAIMediaModerator:
    def __init__(
        self,
        api_key: str | None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key.strip() if api_key else None
        self._transport = transport

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    async def moderate_image(self, image_data: bytes | bytearray) -> TriggerModerationResult:
        if not self.enabled:
            return TriggerModerationResult.SKIPPED

        normalized: bytearray | None = None
        try:
            normalized = await asyncio.to_thread(_normalize_image, image_data)
            return await self._moderate_jpegs([normalized])
        except (OSError, ValueError, UnidentifiedImageError):
            logger.warning("No se pudo preparar una imagen para moderacion.", exc_info=True)
            return TriggerModerationResult.ERROR
        finally:
            _clear_bytearray(normalized)

    async def moderate_video(self, video_data: bytes | bytearray) -> TriggerModerationResult:
        if not self.enabled:
            return TriggerModerationResult.SKIPPED

        frames: list[bytearray] = []
        try:
            frames = await asyncio.to_thread(_extract_video_frames, video_data)
            return await self._moderate_jpegs(frames)
        except (av.FFmpegError, OSError, ValueError):
            logger.warning("No se pudo preparar un video para moderacion.", exc_info=True)
            return TriggerModerationResult.ERROR
        finally:
            for frame in frames:
                _clear_bytearray(frame)
            frames.clear()

    async def _moderate_jpegs(self, jpeg_images: Sequence[bytes | bytearray]) -> TriggerModerationResult:
        input_items: list[dict[str, object]] = []
        try:
            input_items = [
                {
                    "type": "image_url",
                    "image_url": {"url": _jpeg_data_url(image_data)},
                }
                for image_data in jpeg_images
            ]
            async with httpx.AsyncClient(transport=self._transport, timeout=30.0) as client:
                response = await client.post(
                    MODERATIONS_URL,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={"model": MODERATION_MODEL, "input": input_items},
                )
                response.raise_for_status()
                payload = response.json()

            results = payload.get("results")
            if not isinstance(results, list) or not results:
                raise ValueError("La API de moderacion devolvio una respuesta sin resultados.")

            for result in results:
                categories = result.get("categories") if isinstance(result, dict) else None
                if not isinstance(categories, dict):
                    raise ValueError("La API de moderacion devolvio categorias invalidas.")
                if categories.get("sexual") is True or categories.get("sexual/minors") is True:
                    return TriggerModerationResult.BLOCKED
            return TriggerModerationResult.SAFE
        except (httpx.HTTPError, TypeError, ValueError):
            logger.warning("Fallo la consulta al servicio de moderacion.", exc_info=True)
            return TriggerModerationResult.ERROR
        finally:
            input_items.clear()


def trigger_media_kind(media_type: str | None, mime_type: str | None) -> str | None:
    if media_type in {"photo", "sticker"}:
        return "image"
    if media_type in {"video", "video_note"}:
        return "video"
    if media_type == "document" and mime_type:
        if mime_type.casefold().startswith("image/"):
            return "image"
        if mime_type.casefold().startswith("video/"):
            return "video"
    return None


def _uniform_video_frame_times(duration_seconds: float) -> tuple[float, ...]:
    if duration_seconds <= 0:
        raise ValueError("El video no tiene una duracion valida.")
    return tuple(duration_seconds * fraction for fraction in VIDEO_FRAME_FRACTIONS)


def _normalize_image(image_data: bytes | bytearray) -> bytearray:
    with Image.open(io.BytesIO(image_data)) as image:
        image.seek(0)
        normalized = ImageOps.exif_transpose(image).convert("RGB")
        normalized.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
        return _encode_pillow_image(normalized)


def _extract_video_frames(video_data: bytes | bytearray) -> list[bytearray]:
    source = io.BytesIO(video_data)
    frames: list[bytearray] = []
    try:
        with av.open(source, mode="r") as container:
            video_stream = next(iter(container.streams.video), None)
            if video_stream is None:
                raise ValueError("El archivo no contiene video.")

            duration_seconds = _video_duration_seconds(container, video_stream)
            for target_seconds in _uniform_video_frame_times(duration_seconds):
                frames.append(_extract_frame_at(container, video_stream, target_seconds))
        return frames
    except Exception:
        for frame in frames:
            _clear_bytearray(frame)
        raise
    finally:
        source.close()


def _video_duration_seconds(container: av.container.InputContainer, stream: av.video.stream.VideoStream) -> float:
    if stream.duration is not None and stream.time_base is not None:
        duration = float(stream.duration * stream.time_base)
        if duration > 0:
            return duration
    if container.duration is not None:
        duration = float(container.duration / av.time_base)
        if duration > 0:
            return duration
    if stream.frames and stream.average_rate:
        duration = float(stream.frames / stream.average_rate)
        if duration > 0:
            return duration
    raise ValueError("No se pudo determinar la duracion del video.")


def _extract_frame_at(
    container: av.container.InputContainer,
    stream: av.video.stream.VideoStream,
    target_seconds: float,
) -> bytearray:
    if stream.time_base is None:
        raise ValueError("El video no tiene una base de tiempo valida.")

    offset = max(0, int(target_seconds / float(stream.time_base)))
    container.seek(offset, stream=stream, backward=True, any_frame=False)
    selected = None
    for frame in container.decode(stream):
        selected = frame
        if frame.time is not None and frame.time >= target_seconds:
            break
    if selected is None:
        raise ValueError("No se pudo extraer un frame del video.")
    return _encode_pillow_image(selected.to_image().convert("RGB"))


def _encode_pillow_image(image: Image.Image) -> bytearray:
    output = io.BytesIO()
    try:
        image.save(output, format="JPEG", quality=85, optimize=True)
        return bytearray(output.getvalue())
    finally:
        output.close()


def _jpeg_data_url(image_data: bytes | bytearray) -> str:
    encoded = base64.b64encode(image_data).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _clear_bytearray(data: bytearray | None) -> None:
    if data is None:
        return
    data[:] = b"\x00" * len(data)
    data.clear()
