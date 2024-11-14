from discord.ext.commands import Context
from discord.ext import commands
import discord
import asyncio
from discord.utils import get
import time
import yt_dlp as youtube_dl
from Music_player import music_player
from Music_player.yt_search import search
import traceback
from Utils.utils import log

class MediaCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.songsqueue=[]
    
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
    
    @commands.command(name='join',help='join to current channel')
    async def join(self,ctx=Context):
        global voice

        channel = ctx.message.author.voice.channel
        voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)

        if voice and voice.is_connected():
            await voice.move_to(channel)
        else:
            voice = await channel.connect()
            await ctx.send(f'Бот присоединился к голосовому чату: {channel}')
    
    #Отключение
    @commands.command(name='leave',help='leave from current channel')
    async def leave(self,ctx=Context):
        await ctx.voice_client.disconnect()

    @commands.command(name='play',help='play song from current channel')
    async def play(self,ct=Context, url=str()):
        id = ct.message.guild.id
        try:
            channel = ct.message.author.voice.channel
        except:
            await log("WARNING "+str(traceback.format_exc()))
            await ct.send("Подключитесь к голосовому каналу")
            return
        voice = get(self.bot.voice_clients, guild=ct.guild)
        voice_client = ct.message.guild.voice_client
        chk=False
        for i in range(len(self.songsqueue)):
            if self.songsqueue[i][3]==id:
                chk=True
                id=i
                break
        if chk==False:
            s1=asyncio.Queue()
            s2=asyncio.Queue()
            s3=asyncio.LifoQueue()
            s4=asyncio.Queue()
            self.songsqueue.append([s1,s2,s3,id,s4])
            id=len(self.songsqueue)-1
        if len(url)!=0:
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '128',
                }],
                }    
            if "youtu."in url or "www.youtube" in url:
                if "playlist" in url or "start_radio" in url:
                    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                        playlist = url

                    playlist_dict = ydl.extract_info(playlist,download = False)

                    for video in playlist_dict['entries']:
                        for property in ['webpage_url']:
                            url=video.get(property)
                            await log("INFO downloading:"+str(url))
                            await self.songsqueue[id][0].put(url)
                            await self.songsqueue[id][1].put(url)
                    await ct.send("Playlist append to queue")
                else:
                    await self.songsqueue[id][0].put(url)
                    await self.songsqueue[id][1].put(url)
                    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                        await ct.send(str(ydl.extract_info(url, download = False).get('title'))+" append to queue")
            else:
                url=(await search(ct))
                await self.songsqueue[id][0].put(url)
                await self.songsqueue[id][1].put(url)
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    await ct.send(str(ydl.extract_info(url, download = False).get('title'))+" append to queue")
        await log("INFO server"+str(id))
        await log("INFO queue "+str(self.songsqueue))
        try: 
            if voice_client.is_playing() or voice_client.is_paused():
                return
        except:
            pass
        if self.songsqueue[id][0].empty():
            await ct.send("Список песен пуст")
            return
        await ct.send("Приготовтесь, проигрывание начнется скоро")
        try:
            voice = get(self.bot.voice_clients, guild=ct.guild)
            if voice and voice.is_connected():
                await voice.move_to(channel)
            else:
                voice = await channel.connect()
                await ct.send(f'Бот подключился к голосовому каналу: {channel}')
        except:
            await log("WARNING "+str(traceback.format_exc()))
            voice = get(self.bot.voice_clients, guild=ct.guild)
            if voice and voice.is_connected():
                await voice.move_to(channel)
            else:
                voice = await channel.connect()
                await ct.send(f'Бот подключился к голосовому каналу: {channel}')
        else:
            pass
        url= await self.songsqueue[id][0].get()
        url1=url
        await self.songsqueue[id][1].get()
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
        }
        name='Stop'
        if not self.songsqueue[id][1].empty():
            track=await self.songsqueue[id][1].get()
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                name = ydl.extract_info(track, download = False).get('title')
        else:
            name='Stop'
        
        FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 
                        'options': '-vn'}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download = False)#Берем музыку с Ютуба
        #Проверка на стрим
        try:
            if info['live_status']=="is_live":
                stream=True
                duration=0
            else:
                duration=info['duration']
                stream=False
        except:
            duration=info['duration']
            stream=False
        
        URL = info['url']
        voice_client = ct.message.guild.voice_client
        voice.play(discord.FFmpegPCMAudio(URL, **FFMPEG_OPTIONS))
        voice.volume = 100
        voice.is_playing()
        while not(voice_client.is_playing() or voice_client.is_paused()):
            await asyncio.sleep(0.5)
        msgtime=time.time()
        view=music_player.playerView(timeout=36000)
        msg=await ct.send(embed = 
        discord.Embed(
            title = '**C** - ' + info.get('title'),
            description="**Следующая песня:"+name+"     Песен в списке: "+str(self.songsqueue[id][0].qsize())+"**",
            color=0x0033ff),
        view=view)
        ID=msg.id
        voice_client = ct.message.guild.voice_client
        start_time=time.time()
        loop=False
        loopplay=False
        st=str()
        prev=""
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            prev = ydl.extract_info(url, download = False).get('title')
        await self.songsqueue[id][4].put(url)
        while voice_client.is_playing() or voice_client.is_paused() or not self.songsqueue[id][0].empty():#Пока очередь музыки не пуста или музыка проигрывается или стоит на паузе, проигрываем музыку и проверяем очередь
            await asyncio.sleep(1)
            if time.time()-msgtime>60*30:
                msgtime=time.time()
                await msg.delete()
                msg=await ct.send(
                embed = discord.Embed(title = '**Сейчас играет** - ' + info.get('title'),description="**Следующая песня:"+name+"     Песен в списке: "+str(self.songsqueue[id][0].qsize())+"**",color=0x0033ff),
                view=view)
                ID=msg.id
            if view.responce!='' and view.message_id==ID: #Проверка нажатия кнопки
                if view.responce == 'pla':#play pause
                    if voice_client.is_playing():
                        voice_client.pause()
                    elif voice_client.is_paused():
                        voice_client.resume()

                if view.responce =='back':#Перемотка на предыдущую песню
                    if  self.songsqueue[id][2].empty():
                        pass
                    else:
                        voice_client.stop()
                        tostart=asyncio.Queue()
                        while not self.songsqueue[id][0].empty():
                            await tostart.put(await self.songsqueue[id][0].get())
                        while not self.songsqueue[id][1].empty():
                            await self.songsqueue[id][1].get()
                        if not self.songsqueue[id][2].empty():
                            sus=await self.songsqueue[id][2].get()
                            await self.songsqueue[id][0].put(sus)
                            await self.songsqueue[id][0].put(url)
                            await self.songsqueue[id][1].put(url)
                        else:
                            await self.songsqueue[id][0].put(url)
                        while not tostart.empty():
                            sus=await tostart.get()
                            await self.songsqueue[id][0].put(sus)
                            await self.songsqueue[id][1].put(sus)
                        tostart=asyncio.Queue()
                        while self.songsqueue[id][4].qsize()>2:
                            await tostart.put(await self.songsqueue[id][4].get())
                        await self.songsqueue[id][4].get()
                        await self.songsqueue[id][4].get()
                        while not tostart.empty():
                            await self.songsqueue[id][4].put(await tostart.get())
                        url=0

                if view.responce=='skip':#Пропускаем песню с помощью команды стоп
                    if voice_client.is_playing() or voice_client.is_paused():
                        voice_client.stop()
                    else:
                        await ct.send("Бот не проигрывает ничего в данный момент")

                if view.responce =='stop':#Если нажали стоп то очищаем очередь и покидаем voice channel
                    await voice_client.disconnect()
                    while not self.songsqueue[id][0].empty():
                        url = await self.songsqueue[id][0].get()
                    while not self.songsqueue[id][1].empty():
                        url = await self.songsqueue[id][1].get()
                    while not self.songsqueue[id][2].empty():
                        url = await self.songsqueue[id][2].get()
                    await ct.send('Stoped')
                    break
                if view.responce =='loop1':#Если кликнули кнопку лупа то меняем его цвет и включаем луп
                    if loop==False:
                        loop=True
                    else:
                        loop=False
                if view.responce =='loop':#Если кликнули кнопку лупа то меняем его цвет и включаем луп
                    if loopplay==False:
                        loopplay=True
                    else:
                        loopplay=False
                view.responce=""
            if (voice_client.is_playing() or voice_client.is_paused()):
                if stream==True:
                    pass
                elif voice_client.is_playing():#Считаем время песни для проигрывателя, если на паузе сдвигаем стартовое время
                    tim=int(time.time()-int(start_time))
                    S=tim%60
                    M=tim//60
                    st=('{:02d}:{:02d}'.format(M, S))
                    st+=' '
                    percent=int(tim/duration*100)
                    st += (percent // 5) * '▬'
                    st += (20 - (percent // 5)) * '─'
                    st+=' '
                    m = duration//60
                    s = duration%60
                    st+=('{:02d}:{:02d}'.format(m, s))
                    #print(st)
                else:
                    start_time=time.time()-tim
            else:
                if self.songsqueue[id][0].empty() and loop==False and not(voice_client.is_playing() or voice_client.is_paused()):
                    if loopplay==True:
                        await self.songsqueue[id][0].put(await self.songsqueue[id][4].get())
                        while not self.songsqueue[id][4].empty():
                            loo=await self.songsqueue[id][4].get()
                            await self.songsqueue[id][1].put(loo)
                            await self.songsqueue[id][0].put(loo)
                        while not self.songsqueue[id][2].empty():
                            await self.songsqueue[id][2].get()
                    else:
                        await ct.send('Список песен пуст')
                        break
                else:
                    try:
                        if loop==False:#Если зацикливание выключено берем песню из очереди, если включено воспроизводим туже
                            if url!=0:
                                await self.songsqueue[id][2].put(url)
                            if self.songsqueue[id][0].qsize()==self.songsqueue[id][1].qsize():
                                await self.songsqueue[id][1].get()
                            url=await self.songsqueue[id][0].get()
                            await self.songsqueue[id][4].put(url)
                            name='Stop'
                            if loopplay==True and self.songsqueue[id][1].empty():
                                name = ydl.extract_info(url1, download = False).get('title')
                            if not self.songsqueue[id][1].empty():#Берем название следующей песни для проигрывателя, если очередь пуста пишем stop
                                track=await self.songsqueue[id][1].get()
                                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                                    name = ydl.extract_info(track, download = False).get('title')
                            prev=""
                            if not self.songsqueue[id][2].empty():#Берем название следующей песни для проигрывателя, если очередь пуста пишем stop
                                trac=await self.songsqueue[id][2].get()
                                await self.songsqueue[id][2].put(trac)
                                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                                    prev = ydl.extract_info(trac, download = False).get('title')
                            else:
                                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                                    prev = ydl.extract_info(url, download = False).get('title')
                        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(url, download = False)
                        #Проверка на стрим
                        if info['live_status']=="is_live":
                            stream=True
                            duration=0
                        else:
                            duration=info['duration']
                            stream=False

                        URL = info['url']
                        voice.play(discord.FFmpegPCMAudio(URL, **FFMPEG_OPTIONS))
                        voice.volume = 100
                        voice.is_playing()
                        while not(voice_client.is_playing() or voice_client.is_paused()):
                            await asyncio.sleep(0.5)
                        start_time=time.time()
                    except:
                        break
            #Изменение сообщения проигрывателя
            if stream==False:
                await msg.edit(
                embed = discord.Embed(title = '**Сейчас играет** - ' + info.get('title')+'\n'+st,description="**Следующая песня: "+name+'\n'+"     Песен в списке: "+str(self.songsqueue[id][0].qsize())+"**"+'\n'+"**Предыдущая песня: "+prev+"**",color=0x0033ff),view=view)
            else:
                await msg.edit(
                embed = discord.Embed(title = '**Сейчас играет** - ' + info.get('title')+'\n'+"**STREAM**",description="**Следующая песня: "+name+'\n'+"     Песен в списке: "+str(self.songsqueue[id][0].qsize())+"**"+'\n'+"**Предыдущая песня: "+prev+"**",color=0x0033ff),view=view)
        try:
            await ct.voice_client.disconnect()
        except:
            await log("WARNING "+str(traceback.format_exc()))
            pass
async def setup(bot):
    await bot.add_cog(MediaCommands(bot))