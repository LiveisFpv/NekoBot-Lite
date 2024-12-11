import discord
from discord.ext.commands import Context
from discord.ext import commands
import asyncio
import traceback
from Music_player.music_player import playerView
from yt_dlp import YoutubeDL
import yt_dlp
from Utils.utils import log

class MediaPlayer:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.history = asyncio.LifoQueue()
        self.loop = False
        self.loop_playlist = False

    async def add_to_queue(self, url):
        await self.queue.put(url)
        await log(f"INFO: Added to queue: {url}")

    async def get_next_song(self):
        if self.loop:
            return await self.history.get()
        elif not self.queue.empty():
            song = await self.queue.get()
            await self.history.put(song)
            return song
        return None
    async def delete_all_tracks(self):
        while not self.queue.empty():
            await self.queue.get()
        while not self.history.empty():
            await self.history.get()

class MediaCommands(commands.Cog):
    ydl_opts = {
        'format': 'bestaudio/best',
        'ignoreerrors': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
    }
    def __init__(self, bot):
        self.bot = bot
        self.players = {}
    # Выносим блокирующий вызов в отдельный поток
    def fetch_track(self, url):
        with YoutubeDL(self.ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    async def download_video(self,player, video_url):
        await player.add_to_queue(video_url)
    # Выносим блокирующий вызов в отдельный поток
    def fetch_playlist(self,playlist_url):
        ydl_opts = {
            'geo_bypass': True,
            'quiet': True,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'extract_flat': True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(playlist_url, download=False)
    async def download_playlist(self,player,playlist_url):
        playlist_dict = await asyncio.to_thread(self.fetch_playlist, playlist_url)
        tasks = []
        for video in playlist_dict['entries']:
            video_url = video['url']
            await self.download_video(player,video_url)
        await asyncio.gather(*tasks)
    
    async def get_player(self, guild_id)->MediaPlayer:
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

    @commands.command(name='play', help='Play a song from a URL')
    async def play(self, ctx, url: str):
        voice_client = await self.connect_to_channel(ctx)
        if not voice_client:
            return
        player = await self.get_player(ctx.guild.id)
        if "playlist" in url or "list=" in url:
            await self.download_playlist(player, url)
        else:
            await self.download_video(player, url)

        if not voice_client.is_playing():
            await self.start_playback(ctx, voice_client, player)
    async def responce(self,ctx,player,view,voice_client):
        if view.responce=="skip":
            await self.skip(ctx)
        elif view.responce=="play":
            if voice_client.is_playing():
                voice_client.pause()
            else:
                voice_client.resume()
        elif view.responce=="loop":
            if player.loop_playlist:
                player.loop_playlist=False
            else:
                player.loop_playlist=True
        elif view.responce=="loop1":
            if player.loop:
                player.loop=False
            else:
                player.loop=True
        elif view.responce=="stop":
            await player.delete_all_tracks()
            await self.skip(ctx)
    async def start_playback(self, ctx, voice_client, player=MediaPlayer):
        view=playerView(timeout=36000)
        msg= await ctx.send(embed=discord.Embed(title = '**Проигрывание сейчас начнется**'),view=view)
        while not player.queue.empty() or player.loop:
            song = await player.get_next_song()
            if not song:
                break
            try:
                
                info=await asyncio.to_thread(self.fetch_track, song)
                #Пропускаем недоступные треки
                if info==None:
                    continue
                url = info['url']
                FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
                voice_client.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS))
                embed = discord.Embed(title = '**Сейчас играет** - ' + info.get('title'),description="**Следующая песня:"+"name"+"     Песен в списке: "+str(player.queue.qsize())+"**",color=0x0033ff)
                await msg.edit(embed=embed,view=view)
                
                while voice_client.is_playing() or voice_client.is_paused():
                    
                    if view.responce!="":
                        await self.responce(ctx,player,view,voice_client)
                        await msg.edit(view=view)
                        print(view.responce)
                        view.responce=""
                    
                    await asyncio.sleep(1)
            except Exception as e:
                await log(f"ERROR: {traceback.format_exc()}")
                await ctx.send("Произошла ошибка при воспроизведении.")

    #Пропуск трека
    @commands.command(name='skip',help='skip current track')
    async def skip(self,ctx=Context):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()
        else:
            await ctx.send("Бот ничего не проигрывает в данный момент")
    
    #Пауза
    @commands.command(name='pause',help='Pause current track')
    async def pause(self,ctx=Context):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_playing():
            voice_client.pause()
        else:
            await ctx.send("Бот ничего не проигрывает в данный момент")
    
    #Продолжть воспроизведение
    @commands.command(name='resume',help='resume current track')
    async def resume(self,ctx=Context):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_paused():
            voice_client.resume()
        else:
            await ctx.send("Бот ничего не проигрывал до этого. Используйте %play команду")
    @commands.command(name='leave',help='leave from current channel')
    async def leave(self,ctx):
        """Отключить бота от голосового канала."""
        voice_client = ctx.voice_client  # Получаем текущий голосовой клиент
        if voice_client is not None:  # Проверяем, подключён ли бот
            await voice_client.disconnect()
            await ctx.send("Бот отключился от голосового канала.")
        else:
            await ctx.send("Бот не подключён к голосовому каналу.")

async def setup(bot):
    await bot.add_cog(MediaCommands(bot))