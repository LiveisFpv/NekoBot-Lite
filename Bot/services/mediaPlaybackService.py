import asyncio
import traceback

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

    def fetch_track(self, url: str):
        with YoutubeDL(self.ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    def fetch_playlist(self, playlist_url: str):
        with YoutubeDL(self.ydl_opts_meta) as ydl:
            return ydl.extract_info(playlist_url, download=False)

    async def download_video(self, player: MediaPlayer, video_url: str):
        await player.add_to_queue(video_url)

    async def download_playlist(self, player: MediaPlayer, playlist_url: str):
        playlist_dict = await asyncio.to_thread(self.fetch_playlist, playlist_url)
        entries = playlist_dict.get("entries", []) if isinstance(playlist_dict, dict) else []
        for video in entries:
            video_url = video.get("url") if isinstance(video, dict) else None
            if video_url:
                await self.download_video(player, video_url)

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

    @staticmethod
    def _build_now_playing_embed(title: str, next_title: str, queue_size: int):
        return discord.Embed(
            title="**Сейчас играет** - " + title,
            description=(
                "**Следующая песня:"
                + next_title
                + "     Песен в списке: "
                + str(queue_size)
                + "**"
            ),
            color=0x0033FF,
        )

    async def start_playback(self, ctx, voice_client, player: MediaPlayer):
        view = playerView(timeout=36000)
        msg = await ctx.send(
            embed=discord.Embed(title="**Проигрывание сейчас начнется**"),
            view=view,
        )

        while not player.queue.empty() or player.loop:
            song, next_song = await player.get_next_song()
            if not song:
                break

            try:
                info = await asyncio.to_thread(self.fetch_track, song)
                if info is None:
                    continue

                stream_url = info.get("url")
                if not stream_url:
                    await log(f"WARNING: Missing stream URL for track: {song}")
                    continue

                if next_song is not None:
                    info_next = await asyncio.to_thread(self.fetch_track, next_song)
                    next_title = (
                        info_next.get("title") if isinstance(info_next, dict) else "unknown"
                    )
                else:
                    next_title = "end of playlist"

                voice_client.play(discord.FFmpegPCMAudio(stream_url, **self.ffmpeg_options))
                title = info.get("title", song)
                embed = self._build_now_playing_embed(
                    title=title,
                    next_title=next_title,
                    queue_size=player.queue.qsize(),
                )
                await msg.edit(embed=embed, view=view)

                while voice_client.is_playing() or voice_client.is_paused():
                    if view.response != "":
                        await self.handle_view_response(view, player, voice_client)
                        await msg.edit(view=view)
                        view.response = ""
                    await asyncio.sleep(1)

            except Exception:
                await log(f"ERROR: {traceback.format_exc()}")
                await ctx.send("Произошла ошибка при воспроизведении.")
