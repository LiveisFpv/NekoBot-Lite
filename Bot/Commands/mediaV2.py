import asyncio
import os

from discord.ext import commands
from discord.ext.commands import Context

from services.mediaPlaybackService import MediaPlaybackService
from services.mediaService import MediaPlayer


class MediaCommands(commands.Cog):
    YTDLP_REMOTE_COMPONENTS = [
        component.strip()
        for component in os.getenv("YTDLP_REMOTE_COMPONENTS", "ejs:github").split(",")
        if component.strip()
    ]
    YTDLP_JS_RUNTIMES = {"deno": {}}

    YDL_OPTS = {
        "format": "bestaudio/best",
        "ignoreerrors": True,
        "cachedir": os.getenv("YTDLP_CACHE_DIR", "/home/appuser/.cache/yt-dlp"),
        "remote_components": YTDLP_REMOTE_COMPONENTS,
        "js_runtimes": YTDLP_JS_RUNTIMES,
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/113.0.0.0 Safari/537.36"
        ),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }
        ],
    }
    YDL_OPTS_META = {
        "geo_bypass": True,
        "quiet": True,
        "nocheckcertificate": True,
        "ignoreerrors": True,
        "extract_flat": True,
        "cachedir": os.getenv("YTDLP_CACHE_DIR", "/home/appuser/.cache/yt-dlp"),
        "remote_components": YTDLP_REMOTE_COMPONENTS,
        "js_runtimes": YTDLP_JS_RUNTIMES,
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/113.0.0.0 Safari/537.36"
        ),
    }
    FFMPEG_OPTIONS = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn",
    }

    def __init__(self, bot):
        self.bot = bot
        self.players = {}
        self.playback_tasks = {}
        self.playback_locks = {}
        self.playback_service = MediaPlaybackService(
            ydl_opts=self.YDL_OPTS,
            ydl_opts_meta=self.YDL_OPTS_META,
            ffmpeg_options=self.FFMPEG_OPTIONS,
        )

    def get_playback_lock(self, guild_id: int) -> asyncio.Lock:
        if guild_id not in self.playback_locks:
            self.playback_locks[guild_id] = asyncio.Lock()
        return self.playback_locks[guild_id]

    def is_playback_active(self, guild_id: int) -> bool:
        task = self.playback_tasks.get(guild_id)
        return task is not None and not task.done()

    async def run_playback_task(self, guild_id: int, ctx, voice_client, player: MediaPlayer):
        try:
            await self.playback_service.start_playback(ctx, voice_client, player)
        finally:
            self.playback_tasks.pop(guild_id, None)

    async def get_player(self, guild_id) -> MediaPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = MediaPlayer()
        return self.players[guild_id]

    async def connect_to_channel(self, ctx):
        try:
            channel = ctx.author.voice.channel
            voice_client = ctx.voice_client
            if voice_client and voice_client.is_connected():
                await voice_client.move_to(channel)
            else:
                await channel.connect()
            return ctx.guild.voice_client
        except AttributeError:
            await ctx.send("Вы не подключены к голосовому каналу.")
            return None

    @commands.command(name="play", help="Play a song from a URL")
    async def play(self, ctx, url: str):
        voice_client = await self.connect_to_channel(ctx)
        if not voice_client:
            return

        guild_id = ctx.guild.id
        player = await self.get_player(guild_id)
        if "playlist" in url or "list=" in url:
            await self.playback_service.download_playlist(player, url)
        else:
            await self.playback_service.download_video(player, url)

        lock = self.get_playback_lock(guild_id)
        async with lock:
            if not self.is_playback_active(guild_id):
                self.playback_tasks[guild_id] = asyncio.create_task(
                    self.run_playback_task(guild_id, ctx, voice_client, player)
                )

    @commands.command(name="skip", help="skip current track")
    async def skip(self, ctx=Context):
        voice_client = ctx.message.guild.voice_client
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            voice_client.stop()
        else:
            await ctx.send("Бот ничего не проигрывает в данный момент")

    @commands.command(name="pause", help="Pause current track")
    async def pause(self, ctx=Context):
        voice_client = ctx.message.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.pause()
        else:
            await ctx.send("Бот ничего не проигрывает в данный момент")

    @commands.command(name="resume", help="resume current track")
    async def resume(self, ctx=Context):
        voice_client = ctx.message.guild.voice_client
        if voice_client and voice_client.is_paused():
            voice_client.resume()
        else:
            await ctx.send("Бот ничего не проигрывал до этого. Используйте %play команду")

    @commands.command(name="leave", help="leave from current channel")
    async def leave(self, ctx):
        voice_client = ctx.voice_client
        if voice_client is not None:
            await voice_client.disconnect()
            await ctx.send("Бот отключился от голосового канала.")
        else:
            await ctx.send("Бот не подключён к голосовому каналу.")


async def setup(bot):
    await bot.add_cog(MediaCommands(bot))
