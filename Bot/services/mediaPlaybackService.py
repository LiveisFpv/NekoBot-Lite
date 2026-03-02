import asyncio
import traceback
from urllib.parse import urlparse

import discord
from yt_dlp import YoutubeDL

from Music_player.music_player import playerView
from services.mediaService import MediaPlayer
from utils.utils import log


class MediaPlaybackService:
    def __init__(self, ydl_opts: dict, ydl_opts_meta: dict, ffmpeg_options: dict):
        self.ydl_opts = ydl_opts
        self.ydl_opts_meta = ydl_opts_meta
        self.ffmpeg_options = ffmpeg_options

    @staticmethod
    def is_url(value: str) -> bool:
        parsed = urlparse((value or "").strip())
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    def fetch_search_track(self, query: str):
        opts = dict(self.ydl_opts_meta)
        opts["extract_flat"] = False
        opts["quiet"] = True
        opts["noplaylist"] = True
        with YoutubeDL(opts) as ydl:
            return ydl.extract_info(f"ytsearch1:{query}", download=False)

    async def resolve_track_input(self, track_input: str):
        candidate = (track_input or "").strip()
        if not candidate:
            return None, None

        if self.is_url(candidate):
            return candidate, None

        info = await asyncio.to_thread(self.fetch_search_track, candidate)
        if not isinstance(info, dict):
            return None, None

        entries = info.get("entries") or []
        first = next((entry for entry in entries if entry), None)
        if not first:
            return None, None

        resolved_url = first.get("webpage_url")
        if not resolved_url and first.get("id"):
            resolved_url = f"https://www.youtube.com/watch?v={first['id']}"

        return resolved_url, first.get("title")

    def fetch_track(self, url: str):
        with YoutubeDL(self.ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    def fetch_playlist(self, playlist_url: str):
        with YoutubeDL(self.ydl_opts_meta) as ydl:
            return ydl.extract_info(playlist_url, download=False)

    @staticmethod
    def _resolve_entry_url(entry: dict):
        candidate = entry.get("url")
        if isinstance(candidate, str) and candidate.startswith(("http://", "https://")):
            return candidate
        if isinstance(candidate, str) and candidate.strip():
            if entry.get("ie_key") == "Youtube" or entry.get("extractor_key") == "Youtube":
                return f"https://www.youtube.com/watch?v={candidate}"
            return candidate

        webpage_url = entry.get("webpage_url")
        if isinstance(webpage_url, str) and webpage_url.startswith(("http://", "https://")):
            return webpage_url

        video_id = entry.get("id")
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"

        return None

    async def download_video(self, player: MediaPlayer, video_url: str, title: str | None = None):
        await player.add_to_queue(video_url, title=title)

    async def download_playlist(self, player: MediaPlayer, playlist_url: str):
        playlist_dict = await asyncio.to_thread(self.fetch_playlist, playlist_url)
        entries = playlist_dict.get("entries", []) if isinstance(playlist_dict, dict) else []
        for video in entries:
            if not isinstance(video, dict):
                continue
            video_url = self._resolve_entry_url(video)
            if video_url:
                await self.download_video(player, video_url, title=video.get("title"))

    async def handle_view_response(self, view, player: MediaPlayer, voice_client):
        if view.response == "skip":
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()
        elif view.response == "play":
            if voice_client.is_playing():
                voice_client.pause()
            else:
                voice_client.resume()
        elif view.response == "loop":
            player.loop_playlist = not player.loop_playlist
        elif view.response == "loop1":
            player.loop = not player.loop
        elif view.response == "stop":
            await player.delete_all_tracks()
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()
            await voice_client.disconnect()
        elif view.response == "back":
            previous_track = await player.get_previous_song()
            if previous_track and (voice_client.is_playing() or voice_client.is_paused()):
                voice_client.stop()
        elif view.response == "shuffle":
            await player.shuffle_queue()

    @staticmethod
    def _build_now_playing_embed(title: str, next_title: str, queue_size: int):
        return discord.Embed(
            title="**Сейчас играет** - " + title,
            description=(
                "**Следующая песня:"
                + next_title
                + "\nПесен в списке: "
                + str(queue_size)
                + "**"
            ),
            color=0x0033FF,
        )

    @staticmethod
    def _is_voice_active(voice_client) -> bool:
        return voice_client is not None and (voice_client.is_playing() or voice_client.is_paused())

    @staticmethod
    def _is_voice_connected(voice_client) -> bool:
        if voice_client is None:
            return False
        is_connected = getattr(voice_client, "is_connected", None)
        if callable(is_connected):
            try:
                return bool(is_connected())
            except Exception:
                return False
        return True

    async def _send_player_message(self, ctx, embed: discord.Embed, view):
        channel = getattr(ctx, "channel", None)
        if channel is not None:
            return await channel.send(embed=embed, view=view)
        return await ctx.send(embed=embed, view=view)

    async def _safe_edit_player_message(self, message, **kwargs) -> bool:
        if message is None:
            return False
        try:
            await message.edit(**kwargs)
            return True
        except Exception:
            await log(f"WARNING: Failed to edit player message: {traceback.format_exc()}")
            return False

    async def start_playback(self, ctx, voice_client, player: MediaPlayer):
        view = playerView(timeout=36000)
        msg = None

        try:
            msg = await self._send_player_message(
                ctx,
                embed=discord.Embed(title="**Проигрывание сейчас начнется**"),
                view=view,
            )
        except Exception:
            await log(f"WARNING: Failed to send player message: {traceback.format_exc()}")

        while True:
            if not await player.has_pending_tracks():
                if self._is_voice_active(voice_client):
                    await asyncio.sleep(1)
                    continue
                break

            song, _ = await player.get_next_song()
            if not song:
                await asyncio.sleep(1)
                continue

            song_url = song.get("url")
            if not song_url:
                continue

            try:
                info = await asyncio.to_thread(self.fetch_track, song_url)
            except Exception:
                await log(f"ERROR: Failed to fetch track info: {traceback.format_exc()}")
                continue

            if info is None:
                continue

            stream_url = info.get("url")
            if not stream_url:
                await log(f"WARNING: Missing stream URL for track: {song_url}")
                continue

            title = info.get("title") or MediaPlayer.get_track_title(song)
            await player.set_current_track_title(title)

            try:
                voice_client.play(discord.FFmpegPCMAudio(stream_url, **self.ffmpeg_options))
            except Exception:
                await log(f"ERROR: Failed to start playback: {traceback.format_exc()}")
                continue

            last_snapshot = await player.get_status_snapshot()
            if msg is not None:
                ok = await self._safe_edit_player_message(
                    msg,
                    embed=self._build_now_playing_embed(*last_snapshot),
                    view=view,
                )
                if not ok:
                    msg = None

            while self._is_voice_active(voice_client):
                snapshot = await player.get_status_snapshot()
                if msg is not None and snapshot != last_snapshot:
                    ok = await self._safe_edit_player_message(
                        msg,
                        embed=self._build_now_playing_embed(*snapshot),
                        view=view,
                    )
                    if ok:
                        last_snapshot = snapshot
                    else:
                        msg = None

                if view.response != "":
                    try:
                        await self.handle_view_response(view, player, voice_client)
                    except Exception:
                        await log(f"ERROR: Failed to handle player action: {traceback.format_exc()}")
                    finally:
                        if msg is not None:
                            ok = await self._safe_edit_player_message(msg, view=view)
                            if not ok:
                                msg = None
                        view.response = ""

                await asyncio.sleep(1)

        await player.delete_all_tracks()
        if self._is_voice_active(voice_client):
            voice_client.stop()
        if self._is_voice_connected(voice_client):
            await voice_client.disconnect()
