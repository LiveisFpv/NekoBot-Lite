import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.animeService import AnimeService
from services.generalService import GeneralService
from services.lavalinkService import LavalinkService
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


class DummyTrack:
    def __init__(self, title: str, uri: str = "https://example.com", length: int = 180000):
        self.title = title
        self.uri = uri
        self.length = length


class DummyPlaylist:
    def __init__(self, name: str, tracks):
        self.name = name
        self.tracks = list(tracks)

    def __iter__(self):
        return iter(self.tracks)


class DummyQueue:
    def __init__(self):
        self._items = []
        self.mode = None

    def put(self, item):
        if isinstance(item, DummyPlaylist):
            self._items.extend(item.tracks)
            return len(item.tracks)
        if isinstance(item, list):
            self._items.extend(item)
            return len(item)
        self._items.append(item)
        return 1

    def get(self):
        if not self._items:
            raise RuntimeError("queue is empty")
        return self._items.pop(0)

    def put_at(self, index: int, value):
        self._items.insert(index, value)

    def clear(self):
        self._items.clear()

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __bool__(self):
        return bool(self._items)


class DummyPlayer:
    def __init__(self):
        self.queue = DummyQueue()
        self.current = None
        self.playing = False
        self.paused = False
        self.connected = True
        self.position = 0
        self.play_calls = []
        self.skip_calls = 0

    async def play(self, track, **kwargs):
        self.current = track
        self.playing = True
        self.paused = False
        self.play_calls.append((track, kwargs))

    async def pause(self, value: bool):
        self.paused = value
        self.playing = not value

    async def skip(self, force=True):
        self.skip_calls += 1
        self.current = None
        self.playing = False
        self.paused = False

    async def disconnect(self):
        self.connected = False


class DummyMessage:
    def __init__(self, message_id: int):
        self.id = message_id
        self.last_embed = None
        self.last_view = None
        self.edits = 0

    async def edit(self, **kwargs):
        self.last_embed = kwargs.get("embed")
        self.last_view = kwargs.get("view")
        self.edits += 1


class DummyChannel:
    def __init__(self):
        self.messages = {}
        self.sent_count = 0

    async def fetch_message(self, message_id: int):
        if message_id not in self.messages:
            raise RuntimeError("message not found")
        return self.messages[message_id]

    async def send(self, **kwargs):
        self.sent_count += 1
        message = DummyMessage(100 + self.sent_count)
        message.last_embed = kwargs.get("embed")
        message.last_view = kwargs.get("view")
        self.messages[message.id] = message
        return message


class DummyBot:
    def __init__(self, channel):
        self.channel = channel

    def get_channel(self, channel_id: int):
        return self.channel if channel_id == 123 else None


class DummyWavelink:
    Playlist = DummyPlaylist

    class TrackSource:
        YouTubeMusic = "youtube_music"

    class QueueMode:
        normal = "normal"
        loop = "loop"
        loop_all = "loop_all"


@pytest.mark.asyncio
async def test_media_player_previous_song_history():
    state = MediaPlayer()
    track_a = DummyTrack("A")
    track_b = DummyTrack("B")

    await state.push_history(track_a)
    await state.push_history(track_b)

    previous, current = await state.get_previous_song()
    assert previous.title == "A"
    assert current.title == "B"


@pytest.mark.asyncio
async def test_media_player_status_snapshot():
    state = MediaPlayer()
    current = DummyTrack("Now")
    queue = DummyQueue()
    queue.put(DummyTrack("Next"))

    current_title, next_title, queue_size = await state.get_status_snapshot(current, queue)
    assert current_title == "Now"
    assert next_title == "Next"
    assert queue_size == 1


@pytest.mark.asyncio
async def test_media_playback_service_enqueue_playlist(monkeypatch):
    service = MediaPlaybackService()
    player = DummyPlayer()

    monkeypatch.setattr("services.mediaPlaybackService.wavelink", DummyWavelink)

    playlist = DummyPlaylist("Mix", [DummyTrack("A"), DummyTrack("B")])
    monkeypatch.setattr(service, "resolve_tracks", AsyncMock(return_value=playlist))

    result = await service.enqueue_query(player, "playlist query")

    assert result["is_playlist"] is True
    assert result["added"] == 2
    assert len(player.queue) == 2


@pytest.mark.asyncio
async def test_media_playback_service_enqueue_single_track(monkeypatch):
    service = MediaPlaybackService()
    player = DummyPlayer()

    monkeypatch.setattr("services.mediaPlaybackService.wavelink", DummyWavelink)
    monkeypatch.setattr(service, "resolve_tracks", AsyncMock(return_value=[DummyTrack("Song")]))

    result = await service.enqueue_query(player, "song query")

    assert result["is_playlist"] is False
    assert result["added"] == 1
    assert result["title"] == "Song"


def test_media_playback_service_normalize_youtube_playlist_url():
    service = MediaPlaybackService()
    normalized = service.normalize_query(
        "https://youtube.com/playlist?list=PL1234567890&si=abc123"
    )
    assert normalized == "https://www.youtube.com/playlist?list=PL1234567890"


def test_media_playback_service_normalize_youtu_be_url():
    service = MediaPlaybackService()
    normalized = service.normalize_query("https://youtu.be/abcDEF12345?si=zzz")
    assert normalized == "https://www.youtube.com/watch?v=abcDEF12345"


@pytest.mark.asyncio
async def test_media_playback_service_start_if_idle_starts_track():
    service = MediaPlaybackService(default_volume=55)
    player = DummyPlayer()
    player.queue.put(DummyTrack("A"))

    started = await service.start_if_idle(player)

    assert started is True
    assert player.current.title == "A"
    assert player.play_calls[0][1]["volume"] == 55


@pytest.mark.asyncio
async def test_media_playback_service_apply_queue_mode(monkeypatch):
    service = MediaPlaybackService()
    player = DummyPlayer()
    state = MediaPlayer()

    monkeypatch.setattr("services.mediaPlaybackService.wavelink", DummyWavelink)

    await state.set_loop_flags(loop=True)
    await service.apply_queue_mode(player, state)
    assert player.queue.mode == DummyWavelink.QueueMode.loop

    await state.set_loop_flags(loop=False, loop_playlist=True)
    await service.apply_queue_mode(player, state)
    assert player.queue.mode == DummyWavelink.QueueMode.loop_all

    await state.set_loop_flags(loop=False, loop_playlist=False)
    await service.apply_queue_mode(player, state)
    assert player.queue.mode == DummyWavelink.QueueMode.normal


@pytest.mark.asyncio
async def test_media_playback_service_back_button_plays_previous():
    service = MediaPlaybackService()
    player = DummyPlayer()
    state = MediaPlayer()

    track_a = DummyTrack("A")
    track_b = DummyTrack("B")

    await state.push_history(track_a)
    await state.push_history(track_b)

    moved = await service.go_back(player, state)

    assert moved is True
    assert player.current.title == "A"
    assert len(player.queue) == 1
    assert list(player.queue)[0].title == "B"


@pytest.mark.asyncio
async def test_media_playback_service_publish_now_playing_updates_existing(monkeypatch):
    service = MediaPlaybackService()
    player = DummyPlayer()
    player.current = DummyTrack("Now")
    player.queue.put(DummyTrack("Next"))

    state = MediaPlayer()
    await state.set_controller_message(123, 777)

    channel = DummyChannel()
    existing = DummyMessage(777)
    channel.messages[777] = existing
    bot = DummyBot(channel)

    monkeypatch.setattr("services.mediaPlaybackService.wavelink", DummyWavelink)

    await service.publish_now_playing(
        bot,
        1,
        player,
        state,
        action_handler=lambda action, interaction, view: None,
    )

    assert existing.edits == 1
    assert channel.sent_count == 0


@pytest.mark.asyncio
async def test_media_playback_service_publish_now_playing_sends_new_message(monkeypatch):
    service = MediaPlaybackService()
    player = DummyPlayer()
    player.current = DummyTrack("Now")

    state = MediaPlayer()
    await state.set_controller_message(123, None)

    channel = DummyChannel()
    bot = DummyBot(channel)

    monkeypatch.setattr("services.mediaPlaybackService.wavelink", DummyWavelink)

    await service.publish_now_playing(
        bot,
        1,
        player,
        state,
        action_handler=lambda action, interaction, view: None,
    )

    _, message_id = await state.get_controller_message()
    assert channel.sent_count == 1
    assert message_id is not None


def test_lavalink_service_from_env(monkeypatch):
    monkeypatch.setenv("LAVALINK_HOST", "localhost")
    monkeypatch.setenv("LAVALINK_PORT", "2444")
    monkeypatch.setenv("LAVALINK_PASSWORD", "secret")
    monkeypatch.setenv("LAVALINK_SECURE", "true")

    service = LavalinkService.from_env()

    assert service.host == "localhost"
    assert service.port == 2444
    assert service.password == "secret"
    assert service.secure is True
    assert service.uri == "https://localhost:2444"


@pytest.mark.asyncio
async def test_lavalink_service_ensure_connected_uses_existing_nodes(monkeypatch):
    service = LavalinkService(host="lavalink", port=2333, password="pass", secure=False)

    fake_wavelink = SimpleNamespace(Pool=SimpleNamespace(nodes={"main": object()}))
    monkeypatch.setattr("services.lavalinkService.wavelink", fake_wavelink)

    connected = await service.ensure_connected(object())

    assert connected is True
