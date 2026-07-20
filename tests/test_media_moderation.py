from __future__ import annotations

import asyncio
import base64
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import av
from PIL import Image

from galerazo_bot.media_moderation import (
    OpenAIMediaModerator,
    _extract_video_frames,
    _uniform_video_frame_times,
    trigger_media_kind,
)
from galerazo_bot.roles import TriggerModerationResult, TriggerPayload
from galerazo_bot.telegram_bot import _moderate_trigger_payload


def _jpeg(color: str = "white") -> bytearray:
    output = io.BytesIO()
    Image.new("RGB", (16, 16), color).save(output, format="JPEG")
    return bytearray(output.getvalue())


class MediaModerationTests(unittest.TestCase):
    def test_video_samples_use_four_uniform_interior_positions(self) -> None:
        self.assertEqual(_uniform_video_frame_times(10.0), (2.0, 4.0, 6.0, 8.0))

    def test_extracts_exactly_four_frames_from_video_in_memory(self) -> None:
        output = io.BytesIO()
        with av.open(output, mode="w", format="mp4") as container:
            stream = container.add_stream("mpeg4", rate=10)
            stream.width = 64
            stream.height = 64
            stream.pix_fmt = "yuv420p"
            for index in range(20):
                source = Image.new("RGB", (64, 64), (index * 10, 0, 0))
                frame = av.VideoFrame.from_image(source)
                for packet in stream.encode(frame):
                    container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)

        frames = _extract_video_frames(output.getvalue())

        self.assertEqual(len(frames), 4)
        self.assertTrue(all(frame.startswith(b"\xff\xd8") for frame in frames))

    def test_trigger_media_kind_covers_requested_telegram_media(self) -> None:
        self.assertEqual(trigger_media_kind("photo", "image/jpeg"), "image")
        self.assertEqual(trigger_media_kind("sticker", "image/webp"), "image")
        self.assertEqual(trigger_media_kind("document", "image/png"), "image")
        self.assertEqual(trigger_media_kind("video", "video/mp4"), "video")
        self.assertEqual(trigger_media_kind("video_note", "video/mp4"), "video")
        self.assertEqual(trigger_media_kind("document", "video/webm"), "video")
        self.assertIsNone(trigger_media_kind("audio", "audio/ogg"))

    def test_four_video_frames_are_sent_in_one_request_and_cleared(self) -> None:
        captured_inputs = []

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            captured_inputs.extend(payload["input"])
            return httpx.Response(200, json={"results": [{"categories": {"sexual": False}}]})

        frames = [_jpeg(color) for color in ("red", "green", "blue", "white")]
        moderator = OpenAIMediaModerator("test-key", transport=httpx.MockTransport(handler))
        with patch("galerazo_bot.media_moderation._extract_video_frames", return_value=frames):
            result = asyncio.run(moderator.moderate_video(bytearray(b"video")))

        self.assertEqual(result, TriggerModerationResult.SAFE)
        self.assertEqual(len(captured_inputs), 4)
        self.assertTrue(all(item["type"] == "image_url" for item in captured_inputs))
        self.assertTrue(all(not frame for frame in frames))

    def test_sexual_category_blocks_image(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            authorization = request.headers["Authorization"]
            self.assertEqual(authorization, "Bearer test-key")
            payload = json.loads(request.content)
            encoded = payload["input"][0]["image_url"]["url"].split(",", 1)[1]
            self.assertTrue(base64.b64decode(encoded).startswith(b"\xff\xd8"))
            return httpx.Response(200, json={"results": [{"categories": {"sexual": True}}]})

        moderator = OpenAIMediaModerator("test-key", transport=httpx.MockTransport(handler))
        result = asyncio.run(moderator.moderate_image(_jpeg()))

        self.assertEqual(result, TriggerModerationResult.BLOCKED)

    def test_normalized_image_is_cleared_when_api_fails(self) -> None:
        normalized = _jpeg()

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={"error": "unavailable"})

        moderator = OpenAIMediaModerator("test-key", transport=httpx.MockTransport(handler))
        with self.assertLogs("galerazo_bot.media_moderation", level="WARNING"):
            with patch("galerazo_bot.media_moderation._normalize_image", return_value=normalized):
                result = asyncio.run(moderator.moderate_image(bytearray(b"source")))

        self.assertEqual(result, TriggerModerationResult.ERROR)
        self.assertFalse(normalized)

    def test_missing_key_skips_moderation(self) -> None:
        moderator = OpenAIMediaModerator(None)

        result = asyncio.run(moderator.moderate_image(bytearray(b"not-an-image")))

        self.assertEqual(result, TriggerModerationResult.SKIPPED)

    def test_telegram_download_buffer_is_cleared_after_moderation(self) -> None:
        downloaded = bytearray(b"private-media")
        telegram_file = SimpleNamespace(download_as_bytearray=AsyncMock(return_value=downloaded))
        bot = SimpleNamespace(get_file=AsyncMock(return_value=telegram_file))
        moderator = SimpleNamespace(
            enabled=True,
            moderate_image=AsyncMock(return_value=TriggerModerationResult.SAFE),
            moderate_video=AsyncMock(),
        )

        result = asyncio.run(
            _moderate_trigger_payload(
                bot,
                moderator,
                TriggerPayload(media_type="photo", file_id="photo-id", mime_type="image/jpeg"),
            )
        )

        self.assertEqual(result, TriggerModerationResult.SAFE)
        self.assertFalse(downloaded)
        moderator.moderate_image.assert_awaited_once()
        moderator.moderate_video.assert_not_awaited()

    def test_telegram_file_over_20_mb_is_rejected_before_download(self) -> None:
        bot = SimpleNamespace(get_file=AsyncMock())
        moderator = SimpleNamespace(enabled=True)

        result = asyncio.run(
            _moderate_trigger_payload(
                bot,
                moderator,
                TriggerPayload(
                    media_type="video",
                    file_id="video-id",
                    mime_type="video/mp4",
                    moderation_file_size=(20 * 1024 * 1024) + 1,
                ),
            )
        )

        self.assertEqual(result, TriggerModerationResult.TOO_LARGE)
        bot.get_file.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
