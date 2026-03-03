from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import discord

from Music_player.music_player import playerView
from services.mediaService import MediaPlayer
from utils.utils import log

try:
    import wavelink
except Exception:
    wavelink = None


class MediaPlaybackService:
    def __init__(self, *, default_volume: int = 100):
        self.default_volume = default_volume

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
        current_title, next_title, queue_size = await state.get_status_snapshot(current_track, player.queue)
        duration_text = MediaPlayer.format_duration(getattr(current_track, "length", 0))
        position_text = MediaPlayer.format_duration(getattr(player, "position", 0))

        return discord.Embed(
            title=f"**Сейчас играет** - {current_title}",
            description=(
                f"**Следующая песня:** {next_title}\n"
                f"Песен в списке: {queue_size}\n"
                f"Прогресс: {position_text} / {duration_text}"
            ),
            color=0x0033FF,
        )

    async def publish_now_playing(self, bot, guild_id: int, player, state: MediaPlayer, action_handler):
        channel_id, message_id = await state.get_controller_message()
        if channel_id is None:
            return

        channel = bot.get_channel(channel_id)
        if channel is None:
            return

        embed = await self.build_now_playing_embed(player, state)
        view = await self.create_player_view(state, action_handler)

        if message_id:
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(embed=embed, view=view)
                return
            except Exception:
                await log("WARNING: Failed to update controller message. Sending a new one.")

        message = await channel.send(embed=embed, view=view)
        await state.set_controller_message(channel_id, message.id)

    async def skip_to_next(self, player) -> bool:
        if player.current is None and not player.playing and not player.paused:
            return False

        await player.skip(force=True)
        try:
            next_track = player.queue.get()
        except Exception:
            return True

        await player.play(next_track, volume=self.default_volume)
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
