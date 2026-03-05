from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import discord

from Music_player.music_player import playerView
from services.mediaService import MediaPlayer
from services.spotifyService import SpotifyService
from utils.utils import log

try:
    import wavelink
except Exception:
    wavelink = None


@dataclass(frozen=True)
class PlatformStyle:
    platform_id: str
    display_name: str
    color: int
    logo_filename: str | None


class YandexMusicIntegrationError(Exception):
    pass


class YandexMusicConfigError(YandexMusicIntegrationError):
    pass


class YandexMusicApiError(YandexMusicIntegrationError):
    pass


class MediaPlaybackService:
    SOUNDCLOUD_PREVIEW_MIN_MS = 28000
    SOUNDCLOUD_PREVIEW_MAX_MS = 32000
    SPOTIFY_INITIAL_LIMIT = 100

    PLATFORM_STYLES: dict[str, PlatformStyle] = {
        "youtube": PlatformStyle(
            platform_id="youtube",
            display_name="YouTube",
            color=0xFF0000,
            logo_filename="youtube-logo.png",
        ),
        "soundcloud": PlatformStyle(
            platform_id="soundcloud",
            display_name="SoundCloud",
            color=0xFF5500,
            logo_filename="soundcloud-logo.png",
        ),
        "spotify": PlatformStyle(
            platform_id="spotify",
            display_name="Spotify",
            color=0x1DB954,
            logo_filename="spotify-logo.png",
        ),
        "yandexmusic": PlatformStyle(
            platform_id="yandexmusic",
            display_name="Yandex Music",
            color=0xFC3F1D,
            logo_filename="yandex-music-logo.png",
        ),
        "unknown": PlatformStyle(
            platform_id="unknown",
            display_name="Unknown",
            color=0x4F5D75,
            logo_filename=None,
        ),
    }

    def __init__(
        self,
        *,
        default_volume: int = 100,
        spotify_service: SpotifyService | None = None,
        spotify_initial_limit: int = SPOTIFY_INITIAL_LIMIT,
    ):
        self.default_volume = default_volume
        self.spotify_service = spotify_service or SpotifyService()
        self.spotify_initial_limit = max(1, int(spotify_initial_limit))

    @staticmethod
    def _normalize_text(value: object) -> str:
        return str(value or "").strip().lower()

    @staticmethod
    def _is_playlist_result(result) -> bool:
        return wavelink is not None and isinstance(result, wavelink.Playlist)

    @staticmethod
    def _format_track_reference(track) -> str:
        title = MediaPlayer.get_track_title(track)
        uri = getattr(track, "uri", None)
        if uri:
            uri_text = str(uri)
            parsed = urlparse(uri_text)
            if parsed.scheme in {"http", "https"} and parsed.netloc:
                return f"[{title}]({uri_text})"
        return title

    @staticmethod
    def get_track_artwork_url(track) -> str | None:
        if track is None:
            return None

        for attr in ("artwork", "artwork_url", "artworkUrl", "thumbnail", "thumbnail_url", "image"):
            value = getattr(track, attr, None)
            if value:
                return str(value)
        return None

    @classmethod
    def get_platform_style(cls, platform_id: str) -> PlatformStyle:
        return cls.PLATFORM_STYLES.get(platform_id, cls.PLATFORM_STYLES["unknown"])

    @classmethod
    def get_platform_logo_filename(cls, platform_id: str) -> str | None:
        return cls.get_platform_style(platform_id).logo_filename

    @staticmethod
    def detect_platform_id(track) -> str:
        if track is None:
            return "unknown"

        source = MediaPlaybackService._normalize_text(getattr(track, "source", None))
        if source:
            if "soundcloud" in source:
                return "soundcloud"
            if "spotify" in source:
                return "spotify"
            if "yandexmusic" in source or "yandex" in source:
                return "yandexmusic"
            if "youtube" in source or "ytm" in source:
                return "youtube"

        uri = MediaPlaybackService._normalize_text(getattr(track, "uri", None))
        if uri:
            parsed = urlparse(uri)
            host = (parsed.netloc or "").lower()
            if host.startswith("www."):
                host = host[4:]

            if host in {"youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}:
                return "youtube"
            if host == "soundcloud.com" or host.endswith(".soundcloud.com"):
                return "soundcloud"
            if host == "spotify.com" or host.endswith(".spotify.com"):
                return "spotify"
            if host.startswith("music.yandex.") or ".music.yandex." in host:
                return "yandexmusic"

        return "unknown"

    @staticmethod
    def _assets_dir() -> Path:
        return Path(__file__).resolve().parent.parent / "assets"

    @classmethod
    def _asset_path(cls, filename: str) -> Path:
        return cls._assets_dir() / filename

    @classmethod
    def _resolve_logo_filename(cls, platform_id: str) -> str | None:
        logo_filename = cls.get_platform_logo_filename(platform_id)
        if not logo_filename:
            return None
        return logo_filename if cls._asset_path(logo_filename).is_file() else None

    @classmethod
    def _load_platform_logo_file(cls, filename: str | None) -> discord.File | None:
        if not filename:
            return None

        logo_path = cls._asset_path(filename)
        if not logo_path.is_file():
            return None
        return discord.File(str(logo_path), filename=filename)

    @staticmethod
    def _unique_filenames(*filenames: str | None) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for filename in filenames:
            if not filename or filename in seen:
                continue
            seen.add(filename)
            result.append(filename)
        return result

    @staticmethod
    def _get_track_artist(track) -> str:
        for attr in ("author", "artist", "uploader"):
            value = getattr(track, attr, None)
            if value:
                return str(value).strip()
        return ""

    def is_soundcloud_preview_track(self, track) -> bool:
        if track is None or self.detect_platform_id(track) != "soundcloud":
            return False

        for attr in ("is_preview", "isPreview", "preview"):
            value = getattr(track, attr, None)
            if value is not None:
                return bool(value)

        plugin_info = getattr(track, "plugin_info", None) or getattr(track, "pluginInfo", None)
        if isinstance(plugin_info, dict):
            for key in ("is_preview", "isPreview", "preview"):
                if key in plugin_info:
                    return bool(plugin_info.get(key))

        length = getattr(track, "length", None)
        if isinstance(length, (int, float)):
            duration = int(length)
            return self.SOUNDCLOUD_PREVIEW_MIN_MS <= duration <= self.SOUNDCLOUD_PREVIEW_MAX_MS

        return False

    async def search_youtube_music_fallback(self, track):
        if track is None or wavelink is None:
            return None

        title = MediaPlayer.get_track_title(track).strip()
        artist = self._get_track_artist(track)

        if not title:
            return None

        if artist and artist.lower() not in title.lower():
            query = f"{artist} - {title}"
        else:
            query = title

        result = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTubeMusic)
        if not result:
            return None

        if self._is_playlist_result(result):
            tracks = list(result)
            return tracks[0] if tracks else None

        tracks = list(result)
        return tracks[0] if tracks else None

    async def search_youtube_music_track(self, query: str):
        if not query or wavelink is None:
            return None

        result = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTubeMusic)
        if not result:
            return None

        if self._is_playlist_result(result):
            tracks = list(result)
            return tracks[0] if tracks else None

        tracks = list(result)
        return tracks[0] if tracks else None

    async def enqueue_spotify_queries(
        self,
        player,
        queries: list[str],
        *,
        state: MediaPlayer | None = None,
        source_platform: str = "spotify",
    ) -> dict[str, int | str | None]:
        added = 0
        skipped = 0
        first_title: str | None = None

        for query in list(queries or []):
            query_text = str(query or "").strip()
            if not query_text:
                skipped += 1
                continue

            resolved_track = await self.search_youtube_music_track(query_text)
            if resolved_track is None:
                skipped += 1
                continue

            resolved_track = await self.resolve_track_for_playback(resolved_track)
            if state is not None:
                await state.set_track_platforms(
                    resolved_track,
                    added_from=source_platform,
                    playback_via=self.detect_platform_id(resolved_track),
                )

            added += player.queue.put(resolved_track)
            if first_title is None:
                first_title = MediaPlayer.get_track_title(resolved_track)

        return {
            "added": added,
            "skipped": skipped,
            "first_title": first_title,
        }

    async def resolve_track_for_playback(
        self,
        track,
        *,
        force_soundcloud_fallback: bool = False,
    ):
        if track is None or self.detect_platform_id(track) != "soundcloud":
            return track

        if not force_soundcloud_fallback and not self.is_soundcloud_preview_track(track):
            return track

        fallback_track = await self.search_youtube_music_fallback(track)
        if fallback_track is None:
            return track

        await log(
            "INFO: Replaced SoundCloud preview track with YouTube Music fallback: "
            f"{MediaPlayer.get_track_title(track)} -> {MediaPlayer.get_track_title(fallback_track)}"
        )
        return fallback_track

    @staticmethod
    def is_url(value: str) -> bool:
        parsed = urlparse((value or "").strip())
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    @staticmethod
    def is_soundcloud_url(value: str) -> bool:
        parsed = urlparse((value or "").strip())
        if parsed.scheme not in {"http", "https"}:
            return False

        host = (parsed.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]

        return host == "soundcloud.com" or host.endswith(".soundcloud.com")

    @staticmethod
    def is_youtube_url(value: str) -> bool:
        parsed = urlparse((value or "").strip())
        if parsed.scheme not in {"http", "https"}:
            return False

        host = (parsed.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]

        return host in {"youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}

    @staticmethod
    def is_spotify_url(value: str) -> bool:
        parsed = urlparse((value or "").strip())
        if parsed.scheme not in {"http", "https"}:
            return False

        host = (parsed.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]

        return host == "spotify.com" or host.endswith(".spotify.com")

    @staticmethod
    def is_yandex_music_url(value: str) -> bool:
        parsed = urlparse((value or "").strip())
        if parsed.scheme not in {"http", "https"}:
            return False

        host = (parsed.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]

        return host.startswith("music.yandex.") or ".music.yandex." in host

    def detect_source_platform_from_query(self, query: str) -> str:
        candidate = (query or "").strip()
        if self.is_soundcloud_url(candidate):
            return "soundcloud"
        if self.is_youtube_url(candidate):
            return "youtube"
        if self.is_spotify_url(candidate):
            return "spotify"
        if self.is_yandex_music_url(candidate):
            return "yandexmusic"
        return "youtube"

    async def _attach_track_platform_meta(
        self,
        state: MediaPlayer | None,
        original_track,
        final_track,
        *,
        source_platform: str | None = None,
    ) -> None:
        if state is None or final_track is None:
            return

        if source_platform is None:
            existing_added_from, _ = await state.get_track_platforms(original_track)
            if existing_added_from != "unknown":
                source_platform = existing_added_from
            else:
                source_platform = self.detect_platform_id(original_track)

        playback_platform = self.detect_platform_id(final_track)
        await state.set_track_platforms(
            final_track,
            added_from=source_platform,
            playback_via=playback_platform,
        )

        if original_track is not None and original_track is not final_track:
            await state.clear_track_platforms(original_track)

    @staticmethod
    def normalize_query(value: str) -> str:
        candidate = (value or "").strip()
        parsed = urlparse(candidate)
        host = (parsed.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]

        if host not in {"youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}:
            return candidate

        if host == "youtu.be":
            video_id = parsed.path.strip("/")
            if not video_id:
                return candidate
            return f"https://www.youtube.com/watch?v={video_id}"

        query_items = parse_qsl(parsed.query, keep_blank_values=False)
        query_dict = dict(query_items)
        list_id = query_dict.get("list")
        video_id = query_dict.get("v")

        if parsed.path == "/playlist" and list_id:
            return f"https://www.youtube.com/playlist?list={list_id}"

        if parsed.path == "/watch" and list_id and not video_id:
            return f"https://www.youtube.com/playlist?list={list_id}"

        if parsed.path == "/watch" and video_id:
            params = [("v", video_id)]
            if list_id:
                params.append(("list", list_id))
            normalized_query = urlencode(params)
            return urlunparse(("https", "www.youtube.com", "/watch", "", normalized_query, ""))

        return candidate

    async def resolve_tracks(self, query: str):
        if wavelink is None:
            raise RuntimeError("Wavelink is not installed")

        candidate = self.normalize_query(query)
        if not candidate:
            return []

        source = None if self.is_url(candidate) else wavelink.TrackSource.YouTubeMusic
        result = await wavelink.Playable.search(candidate, source=source)
        return result

    async def enqueue_query(self, player, query: str, state: MediaPlayer | None = None):
        if self.is_yandex_music_url(query):
            yandex_token = (os.getenv("YANDEX_TOKEN") or "").strip()
            if not yandex_token:
                raise YandexMusicConfigError(
                    "YANDEX_TOKEN is not configured for Yandex Music URLs."
                )

            try:
                result = await self.resolve_tracks(query)
            except Exception as exc:
                raise YandexMusicApiError(
                    f"Failed to resolve Yandex Music URL: {type(exc).__name__}: {exc}"
                ) from exc

            if not result:
                raise YandexMusicApiError(
                    "Yandex Music URL returned no tracks (service unavailable or URL is not accessible)."
                )

            source_platform = "yandexmusic"

            if self._is_playlist_result(result):
                added = 0
                for original_track in list(result):
                    track = await self.resolve_track_for_playback(original_track)
                    await self._attach_track_platform_meta(
                        state,
                        original_track,
                        track,
                        source_platform=source_platform,
                    )
                    added += player.queue.put(track)
                return {
                    "added": added,
                    "title": result.name,
                    "is_playlist": True,
                    "spotify_deferred_cursor": None,
                }

            tracks = list(result)
            first = tracks[0] if tracks else None
            if first is None:
                raise YandexMusicApiError(
                    "Yandex Music URL returned empty track list."
                )

            first = await self.resolve_track_for_playback(first)
            await self._attach_track_platform_meta(
                state,
                tracks[0],
                first,
                source_platform=source_platform,
            )
            added = player.queue.put(first)
            return {
                "added": added,
                "title": MediaPlayer.get_track_title(first),
                "is_playlist": False,
                "spotify_deferred_cursor": None,
            }

        if self.is_spotify_url(query):
            payload = await self.spotify_service.resolve_for_enqueue(
                query,
                initial_limit=self.spotify_initial_limit,
            )
            enqueue_stats = await self.enqueue_spotify_queries(
                player,
                payload.get("initial_queries") or [],
                state=state,
                source_platform="spotify",
            )
            added = int(enqueue_stats["added"] or 0)
            skipped = int(enqueue_stats["skipped"] or 0)
            kind = str(payload.get("kind") or "track")
            title = str(payload.get("display_title") or enqueue_stats.get("first_title") or "")

            await log(
                "INFO: Spotify import processed "
                f"(kind={kind}, added={added}, skipped={skipped}, deferred="
                f"{'yes' if payload.get('deferred_cursor') else 'no'})"
            )
            return {
                "added": added,
                "title": title or None,
                "is_playlist": kind in {"playlist", "album"},
                "spotify_deferred_cursor": payload.get("deferred_cursor"),
                "spotify_kind": kind,
                "skipped": skipped,
            }

        result = await self.resolve_tracks(query)
        force_soundcloud_fallback = self.is_soundcloud_url(query)
        source_platform = self.detect_source_platform_from_query(query)

        if not result:
            return {"added": 0, "title": None, "is_playlist": False}

        if self._is_playlist_result(result):
            added = 0
            for original_track in list(result):
                track = await self.resolve_track_for_playback(
                    original_track,
                    force_soundcloud_fallback=force_soundcloud_fallback,
                )
                await self._attach_track_platform_meta(
                    state,
                    original_track,
                    track,
                    source_platform=source_platform,
                )
                added += player.queue.put(track)
            return {
                "added": added,
                "title": result.name,
                "is_playlist": True,
                "spotify_deferred_cursor": None,
            }

        tracks = list(result)
        first = tracks[0] if tracks else None
        if first is None:
            return {"added": 0, "title": None, "is_playlist": False}

        first = await self.resolve_track_for_playback(
            first,
            force_soundcloud_fallback=force_soundcloud_fallback,
        )
        await self._attach_track_platform_meta(
            state,
            tracks[0],
            first,
            source_platform=source_platform,
        )
        added = player.queue.put(first)
        return {
            "added": added,
            "title": MediaPlayer.get_track_title(first),
            "is_playlist": False,
            "spotify_deferred_cursor": None,
        }

    async def start_if_idle(self, player, state: MediaPlayer | None = None) -> bool:
        if player.playing or player.paused or player.current is not None:
            return False

        try:
            next_track = player.queue.get()
        except Exception:
            return False

        resolved_track = await self.resolve_track_for_playback(next_track)
        await self._attach_track_platform_meta(state, next_track, resolved_track)
        await player.play(resolved_track, volume=self.default_volume)
        return True

    async def apply_queue_mode(self, player, state: MediaPlayer):
        if wavelink is None:
            return

        loop_one, loop_all = await state.get_loop_flags()
        if loop_one:
            player.queue.mode = wavelink.QueueMode.loop
        elif loop_all:
            player.queue.mode = wavelink.QueueMode.loop_all
        else:
            player.queue.mode = wavelink.QueueMode.normal

    async def create_player_view(self, state: MediaPlayer, action_handler):
        loop_one, loop_all = await state.get_loop_flags()
        return playerView(
            on_action=action_handler,
            loop_enabled=loop_all,
            loop_one_enabled=loop_one,
            timeout=36000,
        )

    async def build_now_playing_embed(self, player, state: MediaPlayer):
        current_track = player.current
        queue_items = list(player.queue)
        next_track = queue_items[0] if queue_items else None
        current_title = MediaPlayer.get_track_title(current_track)
        next_title = MediaPlayer.get_track_title(next_track)
        queue_size = len(queue_items)
        duration_text = MediaPlayer.format_duration(getattr(current_track, "length", 0))
        position_text = MediaPlayer.format_duration(getattr(player, "position", 0))
        progress_text = f"{position_text} / {duration_text}"

        added_from_id, playback_via_id = await state.get_track_platforms(current_track)
        if added_from_id == "unknown":
            added_from_id = self.detect_platform_id(current_track)
        if playback_via_id == "unknown":
            playback_via_id = self.detect_platform_id(current_track)

        source_style = self.get_platform_style(added_from_id)
        playback_style = self.get_platform_style(playback_via_id)

        source_logo_filename = self._resolve_logo_filename(added_from_id)
        playback_logo_filename = self._resolve_logo_filename(playback_via_id)
        source_logo_url = f"attachment://{source_logo_filename}" if source_logo_filename else None
        playback_logo_url = f"attachment://{playback_logo_filename}" if playback_logo_filename else None
        artwork_url = self.get_track_artwork_url(current_track)

        embed = discord.Embed(
            title="Музыкальный плеер",
            description=f"**Сейчас играет:** {self._format_track_reference(current_track)}",
            color=source_style.color,
        )
        embed.add_field(name="Следующий трек", value=self._format_track_reference(next_track), inline=False)
        embed.add_field(name="В очереди", value=str(queue_size), inline=True)
        embed.add_field(name="Прогресс", value=progress_text, inline=True)
        embed.add_field(name="Добавлено из", value=source_style.display_name, inline=True)

        footer_text = (
            f"Воспроизводится через · {playback_style.display_name} | "
            f"Текущий: {current_title} | Далее: {next_title}"
        )
        if playback_logo_url:
            embed.set_footer(text=footer_text, icon_url=playback_logo_url)
        else:
            embed.set_footer(text=footer_text)

        if source_logo_url:
            embed.set_author(name=f"{source_style.display_name}", icon_url=source_logo_url)
        else:
            embed.set_author(name=f"{source_style.display_name}")

        if artwork_url and self.is_url(artwork_url):
            embed.set_thumbnail(url=artwork_url)
        elif source_logo_url:
            embed.set_thumbnail(url=source_logo_url)

        required_logo_filenames = self._unique_filenames(
            source_logo_filename,
            playback_logo_filename,
        )

        return embed, required_logo_filenames

    async def publish_now_playing(self, bot, guild_id: int, player, state: MediaPlayer, action_handler):
        channel_id, message_id = await state.get_controller_message()
        if channel_id is None:
            return

        channel = bot.get_channel(channel_id)
        if channel is None:
            return

        embed, required_logo_filenames = await self.build_now_playing_embed(player, state)
        view = await self.create_player_view(state, action_handler)

        if message_id:
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(embed=embed, view=view)
                return
            except Exception:
                await log("WARNING: Failed to update controller message. Sending a new one.")

        send_kwargs = {"embed": embed, "view": view}
        logo_files: list[discord.File] = []
        for filename in required_logo_filenames:
            file_obj = self._load_platform_logo_file(filename)
            if file_obj is not None:
                logo_files.append(file_obj)
        if logo_files:
            send_kwargs["files"] = logo_files

        message = await channel.send(**send_kwargs)
        await state.set_controller_message(channel_id, message.id)

    async def skip_to_next(self, player) -> bool:
        if player.current is None and not player.playing and not player.paused:
            return False

        await player.skip(force=True)
        return True

    async def go_back(self, player, state: MediaPlayer) -> bool:
        previous_track, current_track = await state.get_previous_song()
        if previous_track is None:
            return False

        if current_track is not None:
            player.queue.put_at(0, current_track)

        resolved_track = await self.resolve_track_for_playback(previous_track)
        await self._attach_track_platform_meta(state, previous_track, resolved_track)
        await player.play(resolved_track, replace=True, volume=self.default_volume)
        return True

    async def handle_view_response(self, action: str, player, state: MediaPlayer) -> bool:
        handled = True

        if action == "skip":
            await self.skip_to_next(player)
        elif action == "play":
            if player.paused:
                await player.pause(False)
            elif player.playing:
                await player.pause(True)
            else:
                await self.start_if_idle(player, state)
        elif action == "loop":
            _, loop_all = await state.get_loop_flags()
            await state.set_loop_flags(loop_playlist=not loop_all)
            await self.apply_queue_mode(player, state)
        elif action == "loop1":
            loop_one, _ = await state.get_loop_flags()
            await state.set_loop_flags(loop=not loop_one)
            await self.apply_queue_mode(player, state)
        elif action == "stop":
            player.queue.clear()
            await state.reset(queue=None)
            if player.current is not None or player.playing or player.paused:
                await player.skip(force=True)
            await player.disconnect()
        elif action == "back":
            await self.go_back(player, state)
        elif action == "shuffle":
            await state.shuffle_queue(player.queue)
        else:
            handled = False

        return handled

    async def handle_track_exception(self, player, state: MediaPlayer | None = None):
        await log("WARNING: Track exception received, attempting to continue queue.")
        if not player.queue:
            return

        try:
            next_track = player.queue.get()
        except Exception:
            return

        resolved_track = await self.resolve_track_for_playback(next_track)
        await self._attach_track_platform_meta(state, next_track, resolved_track)
        await player.play(resolved_track, volume=self.default_volume)
