import json
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.animeService import AnimeService
from services.generalService import GeneralService
from services.mediaPlaybackService import MediaPlaybackService
from services.mediaService import MediaPlayer
from services.memeService import MemeService


class DummyHttpService:
    def __init__(self, json_payload=None, text_payload=None):
        self.json_payload = json_payload
        self.text_payload = text_payload

    async def get_json(self, url: str, headers=None):
        return self.json_payload

    async def get_text(self, url: str, headers=None) -> str:
        return self.text_payload or ""


@pytest.mark.asyncio
async def test_general_service_support_image():
    http_service = DummyHttpService(json_payload={"url": "https://example.com/image.png"})
    service = GeneralService(http_service=http_service)

    image_url = await service.get_support_image_url()

    assert image_url == "https://example.com/image.png"


@pytest.mark.asyncio
async def test_general_service_translate_to_ru():
    service = GeneralService(http_service=DummyHttpService())

    with patch.object(GeneralService, "_translate_to_ru_sync", return_value="привет"):
        result = await service.translate_to_ru("hello")

    assert result == "привет"


@pytest.mark.asyncio
async def test_anime_service_returns_none_for_not_found():
    http_service = DummyHttpService(text_payload="-1")
    service = AnimeService(http_service=http_service)

    result = await service.find_character("naruto")

    assert result is None


@pytest.mark.asyncio
async def test_anime_service_prefers_matching_character():
    payload = {
        "search_results": [
            {"name": "Sakura Haruno"},
            {"name": "Naruto Uzumaki"},
        ]
    }
    http_service = DummyHttpService(text_payload=json.dumps(payload))
    service = AnimeService(http_service=http_service)

    result = await service.find_character("naruto")

    assert result["name"] == "Naruto Uzumaki"


@pytest.mark.asyncio
async def test_meme_service_pikachu_url():
    http_service = DummyHttpService(json_payload={"link": "https://example.com/pikachu.png"})
    service = MemeService(http_service=http_service)

    result = await service.get_pikachu_image_url()

    assert result == "https://example.com/pikachu.png"


@pytest.mark.asyncio
async def test_meme_service_waifu_url():
    http_service = DummyHttpService(json_payload={"url": "https://example.com/waifu.png"})
    service = MemeService(http_service=http_service)

    result = await service.get_waifu_image_url("waifu")

    assert result == "https://example.com/waifu.png"


@pytest.mark.asyncio
async def test_meme_service_translate_to_ru():
    service = MemeService(http_service=DummyHttpService())

    with patch.object(MemeService, "_translate_to_ru_sync", return_value="привет"):
        result = await service.translate_to_ru("hello")

    assert result == "привет"


class DummyVoiceClient:
    def __init__(self, playing=False, paused=False):
        self._playing = playing
        self._paused = paused
        self.stop_called = False
        self.pause_called = False
        self.resume_called = False
        self.disconnected = False

    def is_playing(self):
        return self._playing

    def is_paused(self):
        return self._paused

    def stop(self):
        self.stop_called = True
        self._playing = False
        self._paused = False

    def pause(self):
        self.pause_called = True
        self._playing = False
        self._paused = True

    def resume(self):
        self.resume_called = True
        self._playing = True
        self._paused = False

    async def disconnect(self):
        self.disconnected = True


class DummyView:
    def __init__(self, response):
        self.response = response


@pytest.mark.asyncio
async def test_media_playback_service_download_playlist():
    service = MediaPlaybackService(ydl_opts={}, ydl_opts_meta={}, ffmpeg_options={})
    player = MediaPlayer()

    with patch.object(
        MediaPlaybackService,
        "fetch_playlist",
        return_value={"entries": [{"url": "a"}, {"url": "b"}]},
    ):
        await service.download_playlist(player, "playlist-url")

    first, _ = await player.get_next_song()
    second, _ = await player.get_next_song()
    assert first["url"] == "a"
    assert second["url"] == "b"


@pytest.mark.asyncio
async def test_media_playback_service_handle_view_response_controls():
    service = MediaPlaybackService(ydl_opts={}, ydl_opts_meta={}, ffmpeg_options={})
    player = MediaPlayer()
    voice = DummyVoiceClient(playing=True, paused=False)

    await service.handle_view_response(DummyView("play"), player, voice)
    assert voice.pause_called is True

    await service.handle_view_response(DummyView("play"), player, voice)
    assert voice.resume_called is True

    await service.handle_view_response(DummyView("loop"), player, voice)
    assert player.loop_playlist is True

    await service.handle_view_response(DummyView("loop1"), player, voice)
    assert player.loop is True

    await service.handle_view_response(DummyView("skip"), player, voice)
    assert voice.stop_called is True


@pytest.mark.asyncio
async def test_media_playback_service_handle_view_response_back():
    service = MediaPlaybackService(ydl_opts={}, ydl_opts_meta={}, ffmpeg_options={})
    player = MediaPlayer()
    voice = DummyVoiceClient(playing=True, paused=False)

    await player.add_to_queue("track-a", title="A")
    await player.add_to_queue("track-b", title="B")
    await player.get_next_song()  # A starts playing
    await player.get_next_song()  # B starts playing

    await service.handle_view_response(DummyView("back"), player, voice)
    assert voice.stop_called is True

    previous, _ = await player.get_next_song()
    assert previous["url"] == "track-a"


@pytest.mark.asyncio
async def test_media_playback_service_resolve_track_input_with_url():
    service = MediaPlaybackService(ydl_opts={}, ydl_opts_meta={}, ffmpeg_options={})

    resolved_url, title = await service.resolve_track_input("https://example.com/track")

    assert resolved_url == "https://example.com/track"
    assert title is None


@pytest.mark.asyncio
async def test_media_playback_service_resolve_track_input_with_query():
    service = MediaPlaybackService(ydl_opts={}, ydl_opts_meta={}, ffmpeg_options={})

    with patch.object(
        MediaPlaybackService,
        "fetch_search_track",
        return_value={
            "entries": [
                {
                    "webpage_url": "https://www.youtube.com/watch?v=abc123",
                    "title": "Found song",
                }
            ]
        },
    ):
        resolved_url, title = await service.resolve_track_input("found song query")

    assert resolved_url == "https://www.youtube.com/watch?v=abc123"
    assert title == "Found song"


@pytest.mark.asyncio
async def test_media_player_status_snapshot_updates_on_queue_change():
    player = MediaPlayer()
    await player.add_to_queue("track-a", title="Song A")
    await player.get_next_song()

    current_title, next_title, queue_size, elapsed_seconds, duration_seconds = (
        await player.get_status_snapshot()
    )
    assert current_title == "Song A"
    assert next_title == "end of playlist"
    assert queue_size == 0
    assert elapsed_seconds == 0
    assert duration_seconds is None

    await player.add_to_queue("track-b", title="Song B")
    current_title, next_title, queue_size, elapsed_seconds, duration_seconds = (
        await player.get_status_snapshot()
    )
    assert current_title == "Song A"
    assert next_title == "Song B"
    assert queue_size == 1
    assert elapsed_seconds == 0
    assert duration_seconds is None


@pytest.mark.asyncio
async def test_media_player_elapsed_and_duration_tracking():
    player = MediaPlayer()
    await player.add_to_queue("track-a", title="Song A")
    await player.get_next_song()
    await player.set_current_track_metadata(duration_seconds=120)

    with patch("services.mediaService.time.monotonic", return_value=10):
        await player.begin_current_playback()

    with patch("services.mediaService.time.monotonic", return_value=40):
        _, _, _, elapsed_seconds, duration_seconds = await player.get_status_snapshot()
    assert elapsed_seconds == 30
    assert duration_seconds == 120

    with patch("services.mediaService.time.monotonic", return_value=50):
        await player.mark_paused()

    with patch("services.mediaService.time.monotonic", return_value=80):
        _, _, _, elapsed_seconds, _ = await player.get_status_snapshot()
    assert elapsed_seconds == 40

    with patch("services.mediaService.time.monotonic", return_value=90):
        await player.mark_resumed()

    with patch("services.mediaService.time.monotonic", return_value=100):
        _, _, _, elapsed_seconds, _ = await player.get_status_snapshot()
    assert elapsed_seconds == 50
