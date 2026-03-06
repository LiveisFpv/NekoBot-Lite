import asyncio
import base64
import json
import os
import sys
from collections import deque
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.animeService import AnimeService
from services.generalService import GeneralService
from services.lavalinkService import LavalinkService
from services.mediaPlaybackService import (
    MediaPlaybackService,
    YandexMusicApiError,
    YandexMusicConfigError,
)
from services.mediaService import MediaPlayer
from services.memeService import MemeService
from services.spotifyService import SpotifyConfigError, SpotifyService
from services.httpService import HttpRequestError
from Commands.media import MediaCommands, SpotifyBackfillJob


class DummyHttpService:
    def __init__(
        self,
        json_payload=None,
        text_payload=None,
        json_by_url: dict | None = None,
        text_by_url: dict | None = None,
        post_json_payload=None,
    ):
        self.json_payload = json_payload
        self.text_payload = text_payload
        self.json_by_url = dict(json_by_url or {})
        self.text_by_url = dict(text_by_url or {})
        self.post_json_payload = post_json_payload or {}
        self.last_get_json_url = None
        self.last_post_form_url = None

    async def get_json(self, url: str, headers=None):
        self.last_get_json_url = url
        if url in self.json_by_url:
            payload = self.json_by_url[url]
            if isinstance(payload, Exception):
                raise payload
            if isinstance(payload, list):
                return payload.pop(0) if payload else {}
            return payload
        return self.json_payload

    async def get_text(self, url: str, headers=None) -> str:
        if url in self.text_by_url:
            payload = self.text_by_url[url]
            if isinstance(payload, Exception):
                raise payload
            return str(payload)
        return self.text_payload or ""

    async def post_form_json(self, url: str, data=None, headers=None):
        self.last_post_form_url = url
        return self.post_json_payload


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
    def __init__(
        self,
        title: str,
        uri: str = "https://example.com",
        length: int = 180000,
        source: str | None = None,
        artwork: str | None = None,
        **extra_attrs,
    ):
        self.title = title
        self.uri = uri
        self.length = length
        self.source = source
        self.artwork = artwork
        for key, value in extra_attrs.items():
            setattr(self, key, value)


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
    def __init__(self, message_id: int, attachments=None):
        self.id = message_id
        self.last_embed = None
        self.last_view = None
        self.last_edit_kwargs = None
        self.edits = 0
        self.attachments = list(attachments or [])

    async def edit(self, **kwargs):
        self.last_embed = kwargs.get("embed")
        self.last_view = kwargs.get("view")
        self.last_edit_kwargs = kwargs
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
        files = kwargs.get("files") or []
        attachments = [SimpleNamespace(filename=getattr(item, "filename", "")) for item in files]
        message = DummyMessage(100 + self.sent_count, attachments=attachments)
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
async def test_media_player_track_platform_meta_roundtrip():
    state = MediaPlayer()
    track = DummyTrack("Now")

    await state.set_track_platforms(track, added_from="soundcloud", playback_via="youtube")
    added_from, playback_via = await state.get_track_platforms(track)

    assert added_from == "soundcloud"
    assert playback_via == "youtube"

    await state.clear_track_platforms(track)
    assert await state.get_track_platforms(track) == ("unknown", "unknown")


def test_spotify_service_parse_spotify_url_track_playlist_album_artist():
    ref_track = SpotifyService.parse_spotify_url("https://open.spotify.com/track/abc123?si=zzz")
    ref_playlist = SpotifyService.parse_spotify_url("https://open.spotify.com/playlist/pl123")
    ref_album = SpotifyService.parse_spotify_url("https://open.spotify.com/album/alb123")
    ref_artist = SpotifyService.parse_spotify_url("https://open.spotify.com/artist/art123")

    assert ref_track.kind == "track"
    assert ref_track.entity_id == "abc123"
    assert ref_playlist.kind == "playlist"
    assert ref_playlist.entity_id == "pl123"
    assert ref_album.kind == "album"
    assert ref_album.entity_id == "alb123"
    assert ref_artist.kind == "artist"
    assert ref_artist.entity_id == "art123"


def test_spotify_service_reads_proxy_env(monkeypatch):
    monkeypatch.setenv("SPOTIFY_PROXY_URL", "http://proxy.example:3128")
    monkeypatch.setenv("SPOTIFY_PROXY_USERNAME", "user1")
    monkeypatch.setenv("SPOTIFY_PROXY_PASSWORD", "pass1")

    service = SpotifyService(client_id="client", client_secret="secret")

    assert service.http_service.proxy_url == "http://proxy.example:3128"
    assert service.http_service.proxy_username == "user1"
    assert service.http_service.proxy_password == "pass1"


@pytest.mark.asyncio
async def test_spotify_service_applies_market_to_playlist_tracks_request(monkeypatch):
    monkeypatch.setenv("SPOTIFY_MARKET", "US")
    playlist_id = "PL123"
    expected_url = (
        f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        "?offset=0&limit=50&additional_types=track&market=US"
    )
    http_service = DummyHttpService(
        post_json_payload={"access_token": "token", "expires_in": 3600},
        json_by_url={
            expected_url: {
                "items": [],
                "next": None,
            }
        },
    )
    service = SpotifyService(
        http_service=http_service,
        client_id="client",
        client_secret="secret",
    )

    queries, next_cursor = await service.fetch_deferred_queries(
        {
            "kind": "playlist",
            "entity_id": playlist_id,
            "display_title": "Playlist",
            "offset": 0,
        },
        batch_size=50,
    )

    assert queries == []
    assert next_cursor is None
    assert http_service.last_get_json_url == expected_url


@pytest.mark.asyncio
async def test_spotify_service_resolve_for_enqueue_requires_credentials():
    service = SpotifyService(
        http_service=DummyHttpService(
            post_json_payload={"access_token": "token", "expires_in": 3600},
        ),
        client_id="",
        client_secret="",
    )

    with pytest.raises(SpotifyConfigError):
        await service.resolve_for_enqueue("https://open.spotify.com/track/abc123")


@pytest.mark.asyncio
async def test_spotify_service_resolve_playlist_returns_initial_and_deferred():
    def _playlist_items(start: int, count: int):
        return [
            {
                "track": {
                    "name": f"Song {idx}",
                    "artists": [{"name": f"Artist {idx}"}],
                    "is_local": False,
                }
            }
            for idx in range(start, start + count)
        ]

    playlist_id = "PL123"
    page_0_url = (
        f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        "?offset=0&limit=50&additional_types=track"
    )
    page_50_url = (
        f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        "?offset=50&limit=50&additional_types=track"
    )
    http_service = DummyHttpService(
        post_json_payload={"access_token": "token", "expires_in": 3600},
        json_by_url={
            f"https://api.spotify.com/v1/playlists/{playlist_id}": {"name": "My Playlist"},
            page_0_url: {
                "items": _playlist_items(0, 50),
                "next": f"{page_50_url}",
            },
            page_50_url: {
                "items": _playlist_items(50, 50),
                "next": (
                    f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
                    "?offset=100&limit=50&additional_types=track"
                ),
            },
        },
    )
    service = SpotifyService(
        http_service=http_service,
        client_id="client",
        client_secret="secret",
    )

    payload = await service.resolve_for_enqueue(
        f"https://open.spotify.com/playlist/{playlist_id}",
        initial_limit=100,
    )

    assert payload["kind"] == "playlist"
    assert payload["display_title"] == "My Playlist"
    assert len(payload["initial_queries"]) == 100
    assert payload["initial_queries"][0] == "Artist 0 - Song 0"
    assert payload["deferred_cursor"]["offset"] == 100


@pytest.mark.asyncio
async def test_spotify_service_resolve_artist_returns_top_tracks():
    artist_id = "ART123"
    http_service = DummyHttpService(
        post_json_payload={"access_token": "token", "expires_in": 3600},
        json_by_url={
            f"https://api.spotify.com/v1/artists/{artist_id}?market=US": {"name": "Artist Name"},
            f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=US": {
                "tracks": [
                    {"name": "Song 1", "artists": [{"name": "Artist Name"}]},
                    {"name": "Song 2", "artists": [{"name": "Artist Name"}]},
                ]
            },
        },
    )
    service = SpotifyService(
        http_service=http_service,
        client_id="client",
        client_secret="secret",
    )

    payload = await service.resolve_for_enqueue(
        f"https://open.spotify.com/artist/{artist_id}",
        initial_limit=5,
    )

    assert payload["kind"] == "artist"
    assert payload["display_title"] == "Artist Name"
    assert payload["deferred_cursor"] is None
    assert payload["initial_queries"] == [
        "Artist Name - Song 1",
        "Artist Name - Song 2",
    ]


@pytest.mark.asyncio
async def test_spotify_service_resolve_playlist_uses_web_fallback_on_forbidden():
    playlist_id = "PL403"
    playlist_api_url = f"https://api.spotify.com/v1/playlists/{playlist_id}?market=US"
    initial_state_payload = {
        "entities": {
            "items": {
                f"spotify:playlist:{playlist_id}": {
                    "name": "Fallback Playlist",
                    "content": {
                        "items": [
                            {
                                "itemV2": {
                                    "data": {
                                        "name": "Song A",
                                        "artists": {"items": [{"profile": {"name": "Artist A"}}]},
                                    }
                                }
                            },
                            {
                                "itemV2": {
                                    "data": {
                                        "name": "Song B",
                                        "artists": {"items": [{"profile": {"name": "Artist B"}}]},
                                    }
                                }
                            },
                        ]
                    },
                }
            }
        }
    }
    initial_state_b64 = base64.b64encode(
        json.dumps(initial_state_payload).encode("utf-8")
    ).decode("ascii")
    fallback_html = (
        "<html><head>"
        "<meta property=\"og:title\" content=\"Fallback Playlist\"/>"
        f"<script id=\"initialState\" type=\"text/plain\">{initial_state_b64}</script>"
        "</head><body></body></html>"
    )
    http_service = DummyHttpService(
        post_json_payload={"access_token": "token", "expires_in": 3600},
        json_by_url={
            playlist_api_url: HttpRequestError(
                status=403,
                url=playlist_api_url,
                body='{"error":{"status":403,"message":"Forbidden"}}',
            ),
        },
        text_by_url={
            f"https://open.spotify.com/playlist/{playlist_id}": fallback_html,
        },
    )
    service = SpotifyService(
        http_service=http_service,
        client_id="client",
        client_secret="secret",
    )

    payload = await service.resolve_for_enqueue(
        f"https://open.spotify.com/playlist/{playlist_id}",
        initial_limit=10,
    )

    assert payload["kind"] == "playlist"
    assert payload["display_title"] == "Fallback Playlist"
    assert payload["deferred_cursor"] is None
    assert payload["initial_queries"] == [
        "Artist A - Song A",
        "Artist B - Song B",
    ]


@pytest.mark.asyncio
async def test_spotify_service_resolve_playlist_tracks_forbidden_uses_web_fallback():
    playlist_id = "PL403B"
    playlist_info_url = f"https://api.spotify.com/v1/playlists/{playlist_id}?market=US"
    playlist_tracks_url = (
        f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        "?offset=0&limit=50&additional_types=track&market=US"
    )
    initial_state_payload = {
        "entities": {
            "items": {
                f"spotify:playlist:{playlist_id}": {
                    "name": "Fallback Playlist 2",
                    "content": {
                        "items": [
                            {
                                "itemV2": {
                                    "data": {
                                        "name": "Song X",
                                        "artists": {"items": [{"profile": {"name": "Artist X"}}]},
                                    }
                                }
                            }
                        ]
                    },
                }
            }
        }
    }
    initial_state_b64 = base64.b64encode(
        json.dumps(initial_state_payload).encode("utf-8")
    ).decode("ascii")
    fallback_html = (
        "<html><head>"
        "<meta property=\"og:title\" content=\"Fallback Playlist 2\"/>"
        f"<script id=\"initialState\" type=\"text/plain\">{initial_state_b64}</script>"
        "</head><body></body></html>"
    )
    http_service = DummyHttpService(
        post_json_payload={"access_token": "token", "expires_in": 3600},
        json_by_url={
            playlist_info_url: {"name": "API Playlist Name"},
            playlist_tracks_url: HttpRequestError(
                status=403,
                url=playlist_tracks_url,
                body='{"error":{"status":403,"message":"Forbidden"}}',
            ),
        },
        text_by_url={
            f"https://open.spotify.com/playlist/{playlist_id}": fallback_html,
        },
    )
    service = SpotifyService(
        http_service=http_service,
        client_id="client",
        client_secret="secret",
    )

    payload = await service.resolve_for_enqueue(
        f"https://open.spotify.com/playlist/{playlist_id}",
        initial_limit=10,
    )

    assert payload["kind"] == "playlist"
    assert payload["display_title"] == "Fallback Playlist 2"
    assert payload["deferred_cursor"] is None
    assert payload["initial_queries"] == ["Artist X - Song X"]


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


@pytest.mark.asyncio
async def test_media_playback_service_enqueue_spotify_track_sets_meta(monkeypatch):
    spotify_stub = SimpleNamespace(
        resolve_for_enqueue=AsyncMock(
            return_value={
                "kind": "track",
                "display_title": "Spotify Song",
                "initial_queries": ["Artist - Spotify Song"],
                "deferred_cursor": None,
            }
        )
    )
    service = MediaPlaybackService(spotify_service=spotify_stub)
    player = DummyPlayer()
    state = MediaPlayer()
    matched_track = DummyTrack("Matched", uri="https://youtube.com/watch?v=abc")
    monkeypatch.setattr(service, "search_youtube_music_track", AsyncMock(return_value=matched_track))

    result = await service.enqueue_query(
        player,
        "https://open.spotify.com/track/123",
        state,
    )

    assert result["added"] == 1
    assert result["is_playlist"] is False
    assert result["title"] == "Spotify Song"
    assert await state.get_track_platforms(matched_track) == ("spotify", "youtube")


@pytest.mark.asyncio
async def test_media_playback_service_enqueue_spotify_playlist_returns_deferred_and_skips_non_match(
    monkeypatch,
):
    spotify_stub = SimpleNamespace(
        resolve_for_enqueue=AsyncMock(
            return_value={
                "kind": "playlist",
                "display_title": "Spotify Mix",
                "initial_queries": ["A - One", "B - Two"],
                "deferred_cursor": {"kind": "playlist", "entity_id": "pl1", "offset": 100},
            }
        )
    )
    service = MediaPlaybackService(spotify_service=spotify_stub)
    player = DummyPlayer()
    state = MediaPlayer()
    matched_track = DummyTrack("One", uri="https://youtube.com/watch?v=one")
    monkeypatch.setattr(
        service,
        "search_youtube_music_track",
        AsyncMock(side_effect=[matched_track, None]),
    )

    result = await service.enqueue_query(
        player,
        "https://open.spotify.com/playlist/pl1",
        state,
    )

    assert result["added"] == 1
    assert result["is_playlist"] is True
    assert result["spotify_deferred_cursor"]["offset"] == 100
    assert result["skipped"] == 1
    assert await state.get_track_platforms(matched_track) == ("spotify", "youtube")


@pytest.mark.asyncio
async def test_media_playback_service_enqueue_spotify_raises_config_error():
    spotify_stub = SimpleNamespace(
        resolve_for_enqueue=AsyncMock(side_effect=SpotifyConfigError("missing credentials")),
    )
    service = MediaPlaybackService(spotify_service=spotify_stub)
    player = DummyPlayer()

    with pytest.raises(SpotifyConfigError):
        await service.enqueue_query(player, "https://open.spotify.com/track/123")


@pytest.mark.asyncio
async def test_media_playback_service_enqueue_yandex_track_sets_meta(monkeypatch):
    service = MediaPlaybackService()
    player = DummyPlayer()
    state = MediaPlayer()
    yandex_track = DummyTrack(
        "YM Song",
        uri="https://music.yandex.ru/album/1/track/2",
        source="yandexmusic",
    )

    monkeypatch.setenv("YANDEX_TOKEN", "token")
    monkeypatch.setattr(service, "resolve_tracks", AsyncMock(return_value=[yandex_track]))

    result = await service.enqueue_query(player, "https://music.yandex.ru/album/1/track/2", state)

    assert result["added"] == 1
    assert result["is_playlist"] is False
    assert await state.get_track_platforms(yandex_track) == ("yandexmusic", "yandexmusic")


@pytest.mark.asyncio
async def test_media_playback_service_enqueue_yandex_playlist(monkeypatch):
    service = MediaPlaybackService()
    player = DummyPlayer()
    state = MediaPlayer()
    playlist = DummyPlaylist(
        "YM List",
        [
            DummyTrack("A", uri="https://music.yandex.ru/album/1/track/10", source="yandexmusic"),
            DummyTrack("B", uri="https://music.yandex.ru/album/1/track/11", source="yandexmusic"),
        ],
    )

    monkeypatch.setenv("YANDEX_TOKEN", "token")
    monkeypatch.setattr("services.mediaPlaybackService.wavelink", DummyWavelink)
    monkeypatch.setattr(service, "resolve_tracks", AsyncMock(return_value=playlist))

    result = await service.enqueue_query(player, "https://music.yandex.ru/users/a/playlists/1", state)

    assert result["is_playlist"] is True
    assert result["added"] == 2
    first_track = list(player.queue)[0]
    assert await state.get_track_platforms(first_track) == ("yandexmusic", "yandexmusic")


@pytest.mark.asyncio
async def test_media_playback_service_enqueue_yandex_playlist_skips_ads(monkeypatch):
    service = MediaPlaybackService()
    player = DummyPlayer()
    state = MediaPlayer()
    playlist = DummyPlaylist(
        "YM List",
        [
            DummyTrack("Song A", uri="https://music.yandex.ru/album/1/track/10", source="yandexmusic"),
            DummyTrack("Реклама", uri="https://music.yandex.ru/album/1/track/11", source="yandexmusic", length=30000),
            DummyTrack("Song B", uri="https://music.yandex.ru/album/1/track/12", source="yandexmusic"),
        ],
    )

    monkeypatch.setenv("YANDEX_TOKEN", "token")
    monkeypatch.setattr("services.mediaPlaybackService.wavelink", DummyWavelink)
    monkeypatch.setattr(service, "resolve_tracks", AsyncMock(return_value=playlist))

    result = await service.enqueue_query(player, "https://music.yandex.ru/users/a/playlists/1", state)

    assert result["added"] == 2
    queue_titles = [item.title for item in list(player.queue)]
    assert queue_titles == ["Song A", "Song B"]


def test_media_playback_service_is_yandex_ad_track():
    service = MediaPlaybackService()

    regular = DummyTrack("Song", uri="https://music.yandex.ru/album/1/track/1", source="yandexmusic")
    titled_ad = DummyTrack("Реклама", uri="https://music.yandex.ru/album/1/track/2", source="yandexmusic")
    flagged_ad = DummyTrack(
        "Something",
        uri="https://music.yandex.ru/album/1/track/3",
        source="yandexmusic",
        plugin_info={"type": "ad"},
    )

    assert service.is_yandex_ad_track(regular) is False
    assert service.is_yandex_ad_track(titled_ad) is True
    assert service.is_yandex_ad_track(flagged_ad) is True


@pytest.mark.asyncio
async def test_media_playback_service_enqueue_yandex_requires_token(monkeypatch):
    service = MediaPlaybackService()
    player = DummyPlayer()

    monkeypatch.delenv("YANDEX_TOKEN", raising=False)

    with pytest.raises(YandexMusicConfigError):
        await service.enqueue_query(player, "https://music.yandex.ru/album/1/track/2")


@pytest.mark.asyncio
async def test_media_playback_service_enqueue_yandex_wraps_api_error(monkeypatch):
    service = MediaPlaybackService()
    player = DummyPlayer()

    monkeypatch.setenv("YANDEX_TOKEN", "token")
    monkeypatch.setattr(service, "resolve_tracks", AsyncMock(side_effect=RuntimeError("403 Forbidden")))

    with pytest.raises(YandexMusicApiError):
        await service.enqueue_query(player, "https://music.yandex.ru/album/1/track/2")


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


def test_media_playback_service_detect_platform_id_by_uri():
    service = MediaPlaybackService()

    youtube_track = DummyTrack("YT", uri="https://www.youtube.com/watch?v=abc")
    soundcloud_track = DummyTrack("SC", uri="https://soundcloud.com/artist/song")
    spotify_track = DummyTrack("SP", uri="https://open.spotify.com/track/123")
    yandex_track = DummyTrack("YM", uri="https://music.yandex.ru/album/1/track/2")
    unknown_track = DummyTrack("UNK", uri="https://example.com/audio.mp3")

    assert service.detect_platform_id(youtube_track) == "youtube"
    assert service.detect_platform_id(soundcloud_track) == "soundcloud"
    assert service.detect_platform_id(spotify_track) == "spotify"
    assert service.detect_platform_id(yandex_track) == "yandexmusic"
    assert service.detect_platform_id(unknown_track) == "unknown"


def test_media_playback_service_detect_platform_id_prefers_source():
    service = MediaPlaybackService()

    by_source = DummyTrack(
        "SRC",
        uri="https://example.com",
        source="soundcloud",
    )

    assert service.detect_platform_id(by_source) == "soundcloud"


def test_media_playback_service_get_platform_logo_filename():
    service = MediaPlaybackService()

    assert service.get_platform_logo_filename("youtube") == "youtube-logo.png"
    assert service.get_platform_logo_filename("soundcloud") == "soundcloud-logo.png"
    assert service.get_platform_logo_filename("spotify") == "spotify-logo.png"
    assert service.get_platform_logo_filename("yandexmusic") == "yandex-music-logo.png"
    assert service.get_platform_logo_filename("unknown") is None


def test_media_playback_service_detect_source_platform_from_query():
    service = MediaPlaybackService()

    assert service.detect_source_platform_from_query("https://soundcloud.com/a/b") == "soundcloud"
    assert service.detect_source_platform_from_query("https://youtube.com/watch?v=abc") == "youtube"
    assert service.detect_source_platform_from_query("https://open.spotify.com/track/123") == "spotify"
    assert service.detect_source_platform_from_query("https://music.yandex.ru/album/1/track/2") == "yandexmusic"
    assert service.detect_source_platform_from_query("artist - song") == "youtube"


def test_media_playback_service_is_soundcloud_url():
    service = MediaPlaybackService()

    assert service.is_soundcloud_url("https://soundcloud.com/a/b") is True
    assert service.is_soundcloud_url("https://www.soundcloud.com/a/b") is True
    assert service.is_soundcloud_url("https://youtube.com/watch?v=abc") is False


def test_media_playback_service_is_yandex_music_url():
    service = MediaPlaybackService()

    assert service.is_yandex_music_url("https://music.yandex.ru/album/1/track/2") is True
    assert service.is_yandex_music_url("https://music.yandex.com/album/1") is True
    assert service.is_yandex_music_url("https://open.spotify.com/track/123") is False


def test_media_playback_service_is_soundcloud_preview_by_length():
    service = MediaPlaybackService()
    preview_track = DummyTrack(
        "SC Preview",
        uri="https://soundcloud.com/artist/track",
        length=30000,
    )
    full_track = DummyTrack(
        "SC Full",
        uri="https://soundcloud.com/artist/track-full",
        length=180000,
    )

    assert service.is_soundcloud_preview_track(preview_track) is True
    assert service.is_soundcloud_preview_track(full_track) is False


@pytest.mark.asyncio
async def test_media_playback_service_resolve_track_for_playback_uses_youtube_fallback(monkeypatch):
    service = MediaPlaybackService()
    preview_track = DummyTrack(
        "SC Preview",
        uri="https://soundcloud.com/artist/track",
        length=30000,
    )
    fallback_track = DummyTrack(
        "Fallback",
        uri="https://music.youtube.com/watch?v=fallback",
        length=180000,
    )

    monkeypatch.setattr(service, "search_youtube_music_fallback", AsyncMock(return_value=fallback_track))

    resolved = await service.resolve_track_for_playback(preview_track)
    assert resolved is fallback_track


@pytest.mark.asyncio
async def test_media_playback_service_enqueue_single_track_replaces_soundcloud_preview(monkeypatch):
    service = MediaPlaybackService()
    player = DummyPlayer()
    state = MediaPlayer()
    preview_track = DummyTrack(
        "SC Preview",
        uri="https://soundcloud.com/artist/track",
        length=30000,
    )
    fallback_track = DummyTrack(
        "Fallback Song",
        uri="https://music.youtube.com/watch?v=fallback",
        length=180000,
    )

    monkeypatch.setattr("services.mediaPlaybackService.wavelink", DummyWavelink)
    monkeypatch.setattr(service, "resolve_tracks", AsyncMock(return_value=[preview_track]))
    resolver_mock = AsyncMock(return_value=fallback_track)
    monkeypatch.setattr(service, "resolve_track_for_playback", resolver_mock)

    result = await service.enqueue_query(player, "https://soundcloud.com/artist/track", state)

    assert result["title"] == "Fallback Song"
    assert list(player.queue)[0].title == "Fallback Song"
    resolver_mock.assert_awaited_once_with(
        preview_track,
        force_soundcloud_fallback=True,
    )
    assert await state.get_track_platforms(fallback_track) == ("soundcloud", "youtube")


@pytest.mark.asyncio
async def test_media_playback_service_resolve_tracks_uses_none_source_for_url(monkeypatch):
    service = MediaPlaybackService()
    search_mock = AsyncMock(return_value=[])
    fake_wavelink = SimpleNamespace(
        Playable=SimpleNamespace(search=search_mock),
        TrackSource=SimpleNamespace(YouTubeMusic="youtube_music"),
    )
    monkeypatch.setattr("services.mediaPlaybackService.wavelink", fake_wavelink)

    await service.resolve_tracks("https://soundcloud.com/artist/track")

    search_mock.assert_awaited_once_with("https://soundcloud.com/artist/track", source=None)


@pytest.mark.asyncio
async def test_media_playback_service_resolve_tracks_uses_youtube_music_for_text(monkeypatch):
    service = MediaPlaybackService()
    search_mock = AsyncMock(return_value=[])
    fake_wavelink = SimpleNamespace(
        Playable=SimpleNamespace(search=search_mock),
        TrackSource=SimpleNamespace(YouTubeMusic="youtube_music"),
    )
    monkeypatch.setattr("services.mediaPlaybackService.wavelink", fake_wavelink)

    await service.resolve_tracks("artist - song")

    search_mock.assert_awaited_once_with("artist - song", source="youtube_music")


@pytest.mark.asyncio
async def test_media_playback_service_build_embed_falls_back_to_platform_logo_thumbnail(monkeypatch):
    service = MediaPlaybackService()
    player = DummyPlayer()
    track = DummyTrack("Now", uri="https://youtube.com/watch?v=abc")
    player.current = track
    state = MediaPlayer()
    await state.set_track_platforms(track, added_from="soundcloud", playback_via="youtube")

    monkeypatch.setattr(
        service,
        "_resolve_logo_filename",
        lambda platform_id: "soundcloud-logo.png" if platform_id == "soundcloud" else "youtube-logo.png",
    )

    embed, required_logos = await service.build_now_playing_embed(player, state)

    assert embed.thumbnail.url == "attachment://soundcloud-logo.png"
    assert embed.author.name == "SoundCloud"
    assert embed.author.icon_url == "attachment://soundcloud-logo.png"
    assert embed.footer.text.startswith("Воспроизводится через · YouTube")
    assert embed.footer.icon_url == "attachment://youtube-logo.png"
    assert set(required_logos) == {"soundcloud-logo.png", "youtube-logo.png"}
    assert int(embed.color) == MediaPlaybackService.get_platform_style("soundcloud").color


@pytest.mark.asyncio
async def test_media_playback_service_build_embed_prefers_track_artwork(monkeypatch):
    service = MediaPlaybackService()
    player = DummyPlayer()
    track = DummyTrack(
        "Now",
        uri="https://youtube.com/watch?v=abc",
        artwork="https://img.example.com/artwork.png",
    )
    player.current = track
    state = MediaPlayer()
    await state.set_track_platforms(track, added_from="soundcloud", playback_via="youtube")

    monkeypatch.setattr(service, "_resolve_logo_filename", lambda platform_id: "youtube-logo.png")

    embed, required_logos = await service.build_now_playing_embed(player, state)

    assert embed.thumbnail.url == "https://img.example.com/artwork.png"
    assert set(required_logos) == {"youtube-logo.png"}


@pytest.mark.asyncio
async def test_media_playback_service_build_embed_yandex_platform_style(monkeypatch):
    service = MediaPlaybackService()
    player = DummyPlayer()
    track = DummyTrack(
        "YM",
        uri="https://music.yandex.ru/album/1/track/2",
        source="yandexmusic",
    )
    player.current = track
    state = MediaPlayer()
    await state.set_track_platforms(track, added_from="yandexmusic", playback_via="yandexmusic")

    monkeypatch.setattr(service, "_resolve_logo_filename", lambda platform_id: "yandex-music-logo.png")

    embed, required_logos = await service.build_now_playing_embed(player, state)

    assert embed.author.icon_url == "attachment://yandex-music-logo.png"
    assert embed.footer.icon_url == "attachment://yandex-music-logo.png"
    assert set(required_logos) == {"yandex-music-logo.png"}
    assert int(embed.color) == MediaPlaybackService.get_platform_style("yandexmusic").color


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
async def test_media_playback_service_skip_to_next_only_skips_current():
    service = MediaPlaybackService(default_volume=55)
    player = DummyPlayer()
    player.current = DummyTrack("Current")
    player.playing = True
    player.queue.put(DummyTrack("Next"))

    skipped = await service.skip_to_next(player)

    assert skipped is True
    assert player.skip_calls == 1
    # Wavelink autoplay handles next track; service should not manually call play here.
    assert player.play_calls == []


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
    track = DummyTrack("Now", uri="https://youtube.com/watch?v=abc")
    player.current = track
    player.queue.put(DummyTrack("Next"))

    state = MediaPlayer()
    await state.set_controller_message(123, 777)
    await state.set_track_platforms(track, added_from="youtube", playback_via="youtube")

    channel = DummyChannel()
    existing = DummyMessage(777, attachments=[SimpleNamespace(filename="youtube-logo.png")])
    channel.messages[777] = existing
    bot = DummyBot(channel)

    monkeypatch.setattr(service, "_resolve_logo_filename", lambda platform_id: "youtube-logo.png")

    await service.publish_now_playing(
        bot,
        1,
        player,
        state,
        action_handler=lambda action, interaction, view: None,
    )

    assert existing.edits == 1
    assert channel.sent_count == 0
    assert "attachments" not in (existing.last_edit_kwargs or {})


@pytest.mark.asyncio
async def test_media_playback_service_publish_now_playing_updates_existing_when_attachment_missing(
    monkeypatch,
):
    service = MediaPlaybackService()
    player = DummyPlayer()
    track = DummyTrack("Now", uri="https://youtube.com/watch?v=abc")
    player.current = track

    state = MediaPlayer()
    await state.set_controller_message(123, 777)
    await state.set_track_platforms(track, added_from="youtube", playback_via="youtube")

    channel = DummyChannel()
    existing = DummyMessage(777, attachments=[])
    channel.messages[777] = existing
    bot = DummyBot(channel)

    monkeypatch.setattr(service, "_resolve_logo_filename", lambda platform_id: "youtube-logo.png")

    await service.publish_now_playing(
        bot,
        1,
        player,
        state,
        action_handler=lambda action, interaction, view: None,
    )

    _, message_id = await state.get_controller_message()
    assert channel.sent_count == 0
    assert message_id == 777
    assert existing.edits == 1
    assert "attachments" not in (existing.last_edit_kwargs or {})


@pytest.mark.asyncio
async def test_media_playback_service_publish_now_playing_sends_new_message_without_existing_id(
    monkeypatch,
):
    service = MediaPlaybackService()
    player = DummyPlayer()
    track = DummyTrack("Now", uri="https://youtube.com/watch?v=abc")
    player.current = track

    state = MediaPlayer()
    await state.set_controller_message(123, None)
    await state.set_track_platforms(track, added_from="youtube", playback_via="youtube")

    channel = DummyChannel()
    bot = DummyBot(channel)

    monkeypatch.setattr(
        service,
        "_resolve_logo_filename",
        lambda platform_id: "soundcloud-logo.png" if platform_id == "soundcloud" else "youtube-logo.png",
    )
    monkeypatch.setattr(
        service,
        "_load_platform_logo_file",
        lambda filename: SimpleNamespace(filename=filename),
    )

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
    sent_message = channel.messages[message_id]
    assert {item.filename for item in sent_message.attachments} == {
        "youtube-logo.png",
    }


@pytest.mark.asyncio
async def test_media_commands_spotify_backfill_worker_fifo_order():
    class FakeSpotifyService:
        def __init__(self):
            self.data = {
                "job1": [["q1"], ["q2"]],
                "job2": [["q3"]],
            }

        async def fetch_deferred_queries(self, cursor, batch_size=50):
            key = cursor["key"]
            idx = int(cursor["idx"])
            batch = self.data[key][idx]
            next_idx = idx + 1
            next_cursor = {"key": key, "idx": next_idx} if next_idx < len(self.data[key]) else None
            return batch, next_cursor

    class FakePlaybackService:
        def __init__(self, spotify_service):
            self.spotify_service = spotify_service
            self.calls = []

        async def enqueue_spotify_queries(self, player, queries, *, state=None, source_platform="spotify"):
            self.calls.append((player.tag, list(queries)))
            return {"added": len(queries), "skipped": 0}

    commands = MediaCommands(SimpleNamespace())
    fake_spotify = FakeSpotifyService()
    fake_playback = FakePlaybackService(fake_spotify)
    commands.playback_service = fake_playback

    player = SimpleNamespace(connected=True, tag="P")
    state = MediaPlayer()
    guild_id = 101

    commands._enqueue_spotify_backfill_job(
        guild_id,
        player=player,
        state=state,
        cursor={"key": "job1", "idx": 0},
    )
    commands._enqueue_spotify_backfill_job(
        guild_id,
        player=player,
        state=state,
        cursor={"key": "job2", "idx": 0},
    )

    await commands.spotify_backfill_tasks[guild_id]

    assert fake_playback.calls == [
        ("P", ["q1"]),
        ("P", ["q2"]),
        ("P", ["q3"]),
    ]
    assert guild_id not in commands.spotify_backfill_queues
    assert guild_id not in commands.spotify_backfill_tasks


@pytest.mark.asyncio
async def test_media_commands_cancel_spotify_backfill_clears_state():
    commands = MediaCommands(SimpleNamespace())
    guild_id = 202
    state = MediaPlayer()

    commands.spotify_backfill_queues[guild_id] = deque(
        [
            SpotifyBackfillJob(
                player=SimpleNamespace(connected=True),
                state=state,
                cursor={"key": "job", "idx": 0},
            )
        ]
    )
    task = asyncio.create_task(asyncio.sleep(5))
    commands.spotify_backfill_tasks[guild_id] = task

    commands._cancel_spotify_backfill(guild_id)
    await asyncio.sleep(0)

    assert guild_id not in commands.spotify_backfill_queues
    assert guild_id not in commands.spotify_backfill_tasks
    assert task.cancelled()


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
