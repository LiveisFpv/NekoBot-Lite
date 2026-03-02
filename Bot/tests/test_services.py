import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

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


class DummyPlayerView:
    def __init__(self, timeout=None):
        self.timeout = timeout
        self.response = ""


class DummyMessage:
    def __init__(self, fail_first_edit=False):
        self.fail_first_edit = fail_first_edit
        self.edit_calls = 0

    async def edit(self, **kwargs):
        self.edit_calls += 1
        if self.fail_first_edit and self.edit_calls == 1:
            raise RuntimeError("message edit failed")


class DummyChannel:
    def __init__(self, message):
        self.message = message
        self.send_calls = 0

    async def send(self, **kwargs):
        self.send_calls += 1
        return self.message


class DummyContext:
    def __init__(self, channel):
        self.channel = channel
        self.send_called = False

    async def send(self, *args, **kwargs):
        self.send_called = True
        raise RuntimeError("ctx.send should not be used when channel is available")


class DummyPlaybackVoiceClient:
    def __init__(self, playing_checks=2):
        self._playing = False
        self._paused = False
        self._remaining_checks = playing_checks
        self.play_called = False
        self.stop_called = False
        self.disconnected = False

    def play(self, source):
        self.play_called = True
        self._playing = True
        self._paused = False

    def is_playing(self):
        if not self._playing:
            return False
        if self._remaining_checks <= 0:
            self._playing = False
            return False
        self._remaining_checks -= 1
        return True

    def is_paused(self):
        return self._paused

    def stop(self):
        self.stop_called = True
        self._playing = False
        self._paused = False

    async def disconnect(self):
        self.disconnected = True
        self._playing = False
        self._paused = False

    def is_connected(self):
        return not self.disconnected


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
async def test_media_playback_service_handle_view_response_shuffle():
    service = MediaPlaybackService(ydl_opts={}, ydl_opts_meta={}, ffmpeg_options={})
    player = MediaPlayer()
    voice = DummyVoiceClient(playing=False, paused=False)

    await player.add_to_queue("track-a", title="A")
    await player.add_to_queue("track-b", title="B")
    await player.add_to_queue("track-c", title="C")

    with patch("services.mediaService.random.shuffle", side_effect=lambda items: items.reverse()):
        await service.handle_view_response(DummyView("shuffle"), player, voice)

    first, _ = await player.get_next_song()
    assert first["url"] == "track-c"


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

    current_title, next_title, queue_size = await player.get_status_snapshot()
    assert current_title == "Song A"
    assert next_title == "end of playlist"
    assert queue_size == 0

    await player.add_to_queue("track-b", title="Song B")
    current_title, next_title, queue_size = await player.get_status_snapshot()
    assert current_title == "Song A"
    assert next_title == "Song B"
    assert queue_size == 1


@pytest.mark.asyncio
async def test_media_playback_service_start_playback_uses_channel_send():
    service = MediaPlaybackService(ydl_opts={}, ydl_opts_meta={}, ffmpeg_options={})
    player = MediaPlayer()
    await player.add_to_queue("https://example.com/track", title="Track")

    message = DummyMessage()
    channel = DummyChannel(message)
    ctx = DummyContext(channel)
    voice = DummyPlaybackVoiceClient(playing_checks=1)

    with (
        patch("services.mediaPlaybackService.playerView", DummyPlayerView),
        patch("services.mediaPlaybackService.discord.FFmpegPCMAudio", return_value=MagicMock()),
        patch(
            "services.mediaPlaybackService.asyncio.to_thread",
            new=AsyncMock(return_value={"url": "stream-url", "title": "Track"}),
        ),
        patch("services.mediaPlaybackService.asyncio.sleep", new=AsyncMock()),
    ):
        await service.start_playback(ctx, voice, player)

    assert channel.send_calls == 1
    assert ctx.send_called is False
    assert voice.play_called is True
    assert voice.disconnected is True


@pytest.mark.asyncio
async def test_media_playback_service_start_playback_survives_edit_error():
    service = MediaPlaybackService(ydl_opts={}, ydl_opts_meta={}, ffmpeg_options={})
    player = MediaPlayer()
    await player.add_to_queue("https://example.com/track", title="Track")

    message = DummyMessage(fail_first_edit=True)
    channel = DummyChannel(message)
    ctx = DummyContext(channel)
    voice = DummyPlaybackVoiceClient(playing_checks=2)

    with (
        patch("services.mediaPlaybackService.playerView", DummyPlayerView),
        patch("services.mediaPlaybackService.discord.FFmpegPCMAudio", return_value=MagicMock()),
        patch(
            "services.mediaPlaybackService.asyncio.to_thread",
            new=AsyncMock(return_value={"url": "stream-url", "title": "Track"}),
        ),
        patch("services.mediaPlaybackService.asyncio.sleep", new=AsyncMock()),
    ):
        await service.start_playback(ctx, voice, player)

    assert voice.play_called is True
    assert voice.stop_called is False
    assert voice.disconnected is True
