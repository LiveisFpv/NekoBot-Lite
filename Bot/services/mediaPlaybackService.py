from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import discord

from Music_player.music_player import playerView
from services.mediaService import MediaPlayer
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


class MediaPlaybackService:
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
        "unknown": PlatformStyle(
            platform_id="unknown",
            display_name="Unknown",
            color=0x4F5D75,
            logo_filename=None,
        ),
    }

    def __init__(self, *, default_volume: int = 100):
        self.default_volume = default_volume

    @staticmethod
    def _normalize_text(value: object) -> str:
        return str(value or "").strip().lower()

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
    def _message_has_attachment(message, filename: str) -> bool:
        attachments = getattr(message, "attachments", [])
        return any(getattr(item, "filename", "") == filename for item in attachments)

    @staticmethod
    def is_url(value: str) -> bool:
        parsed = urlparse((value or "").strip())
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

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

    async def enqueue_query(self, player, query: str):
        result = await self.resolve_tracks(query)

        if not result:
            return {"added": 0, "title": None, "is_playlist": False}

        if isinstance(result, wavelink.Playlist):
            added = player.queue.put(result)
            return {
                "added": added,
                "title": result.name,
                "is_playlist": True,
            }

        tracks = list(result)
        first = tracks[0] if tracks else None
        if first is None:
            return {"added": 0, "title": None, "is_playlist": False}

        added = player.queue.put(first)
        return {
            "added": added,
            "title": MediaPlayer.get_track_title(first),
            "is_playlist": False,
        }

    async def start_if_idle(self, player) -> bool:
        if player.playing or player.paused or player.current is not None:
            return False

        try:
            next_track = player.queue.get()
        except Exception:
            return False

        await player.play(next_track, volume=self.default_volume)
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

        platform_id = self.detect_platform_id(current_track)
        platform_style = self.get_platform_style(platform_id)
        logo_filename = self._resolve_logo_filename(platform_id)
        logo_url = f"attachment://{logo_filename}" if logo_filename else None
        artwork_url = self.get_track_artwork_url(current_track)

        embed = discord.Embed(
            title="Музыкальный плеер",
            description=f"**Сейчас играет:** {self._format_track_reference(current_track)}",
            color=platform_style.color,
        )
        embed.add_field(name="Следующий трек", value=self._format_track_reference(next_track), inline=False)
        embed.add_field(name="Платформа", value=platform_style.display_name, inline=True)
        embed.add_field(name="В очереди", value=str(queue_size), inline=True)
        embed.add_field(name="Прогресс", value=progress_text, inline=True)
        embed.set_footer(text=f"Текущий трек: {current_title} | Далее: {next_title}")

        if logo_url:
            embed.set_author(name=f"Сейчас играет · {platform_style.display_name}", icon_url=logo_url)
        else:
            embed.set_author(name=f"Сейчас играет · {platform_style.display_name}")

        if artwork_url and self.is_url(artwork_url):
            embed.set_thumbnail(url=artwork_url)
        elif logo_url:
            embed.set_thumbnail(url=logo_url)

        return embed, logo_filename

    async def publish_now_playing(self, bot, guild_id: int, player, state: MediaPlayer, action_handler):
        channel_id, message_id = await state.get_controller_message()
        if channel_id is None:
            return

        channel = bot.get_channel(channel_id)
        if channel is None:
            return

        embed, logo_filename = await self.build_now_playing_embed(player, state)
        view = await self.create_player_view(state, action_handler)

        if message_id:
            try:
                message = await channel.fetch_message(message_id)
                if logo_filename and not self._message_has_attachment(message, logo_filename):
                    await log(
                        "INFO: Controller message has no platform logo attachment. "
                        "Sending a new controller message."
                    )
                else:
                    await message.edit(embed=embed, view=view)
                    return
            except Exception:
                await log("WARNING: Failed to update controller message. Sending a new one.")

        send_kwargs = {"embed": embed, "view": view}
        logo_file = self._load_platform_logo_file(logo_filename)
        if logo_file is not None:
            send_kwargs["files"] = [logo_file]

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

        await player.play(previous_track, replace=True, volume=self.default_volume)
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
                await self.start_if_idle(player)
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

    async def handle_track_exception(self, player):
        await log("WARNING: Track exception received, attempting to continue queue.")
        if not player.queue:
            return

        try:
            next_track = player.queue.get()
        except Exception:
            return

        await player.play(next_track, volume=self.default_volume)
