# - * - coding: utf-8 - * -
import io
import requests
import discord
import json
from discord.utils import get
from discord.ext import commands
from discord.ext.commands import Context
import asyncio
import asyncpraw
import random
from discord import ButtonStyle
from discord.ui import Button, View
from googletrans import Translator
#import pytesseract
from requests.api import request
import yt_dlp as youtube_dl
import time
from yt_dlp import YoutubeDL
from timeit import default_timer as timer
from datetime import timedelta
import traceback
from PIL import Image, ImageDraw, ImageFont
start = timer()

translate = Translator()

settings = json.load(open("bot.json","r"))
reddit_api = json.load(open("reddit.json","r"))
intents = discord.Intents.all()

bot = commands.Bot(command_prefix = settings['prefix'],intents=intents,help_command=None)

check=False
starttime=time.time()

async def log(str):
    print(str)

async def status():
    while True:
        print("Online:"+str(timedelta(seconds=timer()-start)), end="\r")
        await log("INFO Online:"+str(timedelta(seconds=timer()-start)))
        await asyncio.sleep(600)

@bot.command()# Перевод текста
async def trans(ctx=Context): # Создаём функцию и передаём аргумент ctx(информация о сообщении).
    sr=ctx.message.content.split("%trans")
    stre=str()
    for i in sr:
        stre+=i
    result = translate.translate(text=stre,dest='ru')
    await ctx.send(result.text)

@bot.command()# Не передаём аргумент pass_context, так как он был нужен в старых версиях.
async def version(ctx=Context): # Создаём функцию и передаём аргумент ctx.
    embed=discord.Embed(title="NEKO bot lite Версия 1.5 Бета:", description=f"**Обновления:**Добавлены новые более быстрые кнопки\nОбновлна версия Python до 3.12.4 и библиотека discord\n**Пофиксены некоторые баги\nДобавлена мини игра**\nПоследнее обновлние:15.08.2024", color=0x0033ff)
    r = requests.get("https://api.waifu.pics/sfw/"+"neko")
    imageurl=r.json()["url"]
    embed.set_image(url=imageurl)
    await ctx.send(embed=embed)

@bot.command()# Не передаём аргумент pass_context, так как он был нужен в старых версиях.
async def help(ctx=Context): # Создаём функцию и передаём аргумент ctx.
    embed=discord.Embed(title="NEKO bot lite commands:", description=f"""**%version**-Версия бота и описание последнего обновления
        **%pikachu**- Отправляет рандомного пикачу
        **%Reddit 'Название группы'**-Отправляет рандомный пост из этой группы
        **%anime**-Выводит рандомную аниме цитату
        **%meme**- Рандомный популярный мем
        **%potato**- КАРТОШКА
        **%genshin**-Все для геншинфагов
        **%animeme**-Анимешные мемы тоже в чате
        **%trans**- Для свободного взаимодействия
        **%loli-Используйте эту команду только в том случае, если хотите сесть в тюрьму на 8 лет, но 8 лет – не срок…**
        В полной версии автоматически переводит мемы
        В этой присутствуют мини игры
        **%FBI-FBI OPEN UP**
        **%c**-Найти аниме с этим персонажем
        **%waifu**-print **'%waifu help'** Чтобы увидеть список доступных для этой команд
        **%neko-NEKOCHAN!!!!!** Неко неко неко
        *%support*
        *Created by LiveisFPV*""", color=0x0033ff)
    embed.set_author(name="NEKO", icon_url=bot.user.avatar.url)
    r = requests.get("https://api.waifu.pics/sfw/"+"neko")
    imageurl=r.json()["url"]
    embed.set_image(url=imageurl)
    await ctx.send(embed=embed)
    embed=discord.Embed(title="MUSIC commands:", description=f"""**%play**-Воспроизвети/добавить трек/плейлист или найти песню
        **%pause**-Поставить на паузу
        **%resume**-Продолжить
        **%skip**-Пропустить трек
        **Кнопки:
        Back
        Play/pause
        Skip
        Loop queue
        Stop and leave
        Loop track**""",color=0x0033ff)
    embed.set_author(name="NEKO", icon_url=bot.user.avatar.url)
    embed.set_image(url="https://images.pexels.com/photos/3104/black-and-white-music-headphones-life.jpg?auto=compress&cs=tinysrgb&dpr=2&h=750&w=1260")
    await ctx.send(embed=embed)

@bot.command()# Не передаём аргумент pass_context, так как он был нужен в старых версиях.
async def FBI(ctx=Context): # Создаём функцию и передаём аргумент ctx.
    embed=discord.Embed(title="CALL FBI")
    embed.set_image(url = "https://static.life.ru/publications/2021/0/7/647334249696.4198.gif")
    await ctx.send(embed=embed)
    await asyncio.sleep(5)
    embed=discord.Embed(title="FBI SO CLOSE")
    embed.set_image(url = "https://i.gifer.com/origin/b3/b3d55ae5d60049304d0bd8a4619efa59.gif")
    await ctx.send(embed=embed)
    await asyncio.sleep(5)
    embed=discord.Embed(title="FBI OPEN UP")
    embed.set_image(url = "https://c.tenor.com/_YqdfwYLiQ4AAAAC/traffic-fbi-open-up.gif")
    await ctx.send(embed=embed)
#Snake
class Snake(View):
    def __init__(self):
        super().__init__(timeout=36000)
        self.goto="R"
        self.matrix=[["◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️"] for i in range(12)]
        self.coords=[[0,0],[1,0],[2,0]]
        self.apple=[2,2]
        self.image=Image.new('RGB',(240,240),'black')
        self.embed=discord.Embed(title="Snake game")
        self.score=0
        self.gameover=0
        with io.BytesIO() as image_binary:
                self.image.save(image_binary,"PNG")
                image_binary.seek(0)
                self.file=discord.File(fp=image_binary, filename='image.png')
    async def apple_update(self):
        check=0
        while self.apple in self.coords:
            self.apple=[(random.randint(0,11)),(random.randint(0,11))]
            check=1
        return check
    async def snake_update(self):
        check=0
        if self.goto=="R":
            if self.coords[-1][0]+1>=12 or [self.coords[-1][0]+1,self.coords[-1][1]] in self.coords:
                self.gameover=1
            else:
                self.coords.append([self.coords[-1][0]+1,self.coords[-1][1]])
                check=await self.apple_update()
        elif self.goto=="L":
            if self.coords[-1][0]-1<0 or [self.coords[-1][0]-1,self.coords[-1][1]] in self.coords:
                self.gameover=1
            else:
                self.coords.append([self.coords[-1][0]-1,self.coords[-1][1]])
                check=await self.apple_update()
        elif self.goto=="U":
            if self.coords[-1][1]-1<0 or [self.coords[-1][0],self.coords[-1][1]-1] in self.coords:
                self.gameover=1
            else:
                self.coords.append([self.coords[-1][0],self.coords[-1][1]-1])
                check=await self.apple_update()
        elif self.goto=="D":
            if self.coords[-1][1]+1>=12 or [self.coords[-1][0],self.coords[-1][1]+1] in self.coords:
                self.gameover=1
            else:
                self.coords.append([self.coords[-1][0],self.coords[-1][1]+1])
                check=await self.apple_update()
        pass
        if not check and not self.gameover:
            self.coords.pop(0)
        else:
            self.score+=10
    async def retext(self):
        await self.snake_update()
        self.matrix=[["◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️"] for i in range(12)]
        for coord in self.coords:
            self.matrix[coord[1]][coord[0]]="🟩"
        self.matrix[self.apple[1]][self.apple[0]]="🟥"
    async def redraw(self):
        await self.snake_update()
        self.image=Image.new('RGB',(240,240),'black')
        idraw=ImageDraw.Draw(self.image)
        for coord in self.coords:
            idraw.rectangle((coord[0]*20,coord[1]*20,(coord[0]+1)*20,(coord[1]+1)*20),fill="green")
        idraw.rectangle((self.apple[0]*20,self.apple[1]*20,(self.apple[0]+1)*20,(self.apple[1]+1)*20),fill="red")
        pass
    async def get_image(self):
        await asyncio.sleep(0.4)
        await self.redraw()
        with io.BytesIO() as image_binary:
            self.image.save(image_binary,"PNG")
            image_binary.seek(0)
            self.file=discord.File(fp=image_binary, filename='image.png')
            self.embed.set_image(url=("attachment://"+self.file.filename))
        return self.file, self.embed
    async def get_text(self):
        await asyncio.sleep(0.4)
        await self.retext()
        s=""
        for elements in self.matrix:
            for element in elements:
                s+=element
            s+='\n'
        self.embed.description="**"+s+"**"
        if self.gameover:
            self.embed.title="Score: "+str(self.score-10)
        return self.embed,self.gameover
    @discord.ui.button(style = ButtonStyle.grey,emoji = '🔴',custom_id = "00",row=0)
    async def button_callback00(self,interaction: discord.Interaction,button:Button):
        await interaction.response.defer()
    @discord.ui.button(style = ButtonStyle.grey,emoji = '⬆️',custom_id = "01",row=0)
    async def button_callback01(self,interaction: discord.Interaction,button:Button):
        if self.goto!="D":
            self.goto="U"
        await interaction.response.defer()
    @discord.ui.button(style = ButtonStyle.grey,emoji = '🔴',custom_id = "02",row=0)
    async def button_callback02(self,interaction: discord.Interaction,button:Button):
        await interaction.response.defer()
    @discord.ui.button(style = ButtonStyle.grey,emoji = '⬅️',custom_id = "10",row=1)
    async def button_callback10(self,interaction: discord.Interaction,button:Button):
        if self.goto!="R":
            self.goto="L"
        await interaction.response.defer()
    @discord.ui.button(style = ButtonStyle.grey,emoji = '⬇️',custom_id = "11",row=1)
    async def button_callback11(self,interaction: discord.Interaction,button:Button):
        if self.goto!="U":
            self.goto="D"
        await interaction.response.defer()
    @discord.ui.button(style = ButtonStyle.grey,emoji = '➡️',custom_id = "12",row=1)
    async def button_callback12(self,interaction: discord.Interaction,button:Button):
        if self.goto!="L":
            self.goto="R"
        await interaction.response.defer()
       
@bot.command()
async def snake(ctx=Context,name="text"):
    view=Snake()
    if name!="text":
        file,embed=await view.get_image()
        msg= await ctx.send(file=file,embed=embed)
        while True:
            file,embed=await view.get_image()
            await msg.edit(embed=embed,attachments=[file],view=view)
    else:
        embed,over=await view.get_text()
        msg= await ctx.send(embed=embed,view=view)
        while not over:
            embed,over=await view.get_text()
            await msg.edit(embed=embed)
    view.stop()
    del view
#MUSIC
songsqueue=[]
class playerView(View):
    responce=''
    message_id=''
    LOOP=ButtonStyle.grey
    LOOPSTYLE=ButtonStyle.grey
    
    @discord.ui.button(style = ButtonStyle.grey,emoji = '⏮',custom_id = "back",row=0)
    async def button_callback1(self,interaction: discord.Interaction,button:Button):
        self.responce="back"
        self.message_id=interaction.message.id
        await interaction.response.defer()
        
    @discord.ui.button(style = ButtonStyle.grey,emoji = '⏯',custom_id = "pla",row=0)
    async def button_callback2(self,interaction: discord.Interaction,button:Button):
        self.responce="pla"
        self.message_id=interaction.message.id
        await interaction.response.defer()
        
    @discord.ui.button(style = ButtonStyle.grey,emoji = '⏭',custom_id = "skip",row=0)
    async def button_callback3(self,interaction: discord.Interaction,button:Button):
        self.responce="skip"
        self.message_id=interaction.message.id
        await interaction.response.defer()
        
    @discord.ui.button(style = ButtonStyle.grey,emoji = '🔁',custom_id = "loop",row=1)
    async def button_callback4(self,interaction: discord.Interaction,button:Button):
        self.responce="loop"
        self.message_id=interaction.message.id
        if button.style==ButtonStyle.green:
            button.style=ButtonStyle.grey
        else:
            button.style=ButtonStyle.green
        await interaction.response.defer()
        
    @discord.ui.button(style = ButtonStyle.grey,emoji = '🔂',custom_id = "loop1",row=1)
    async def button_callback5(self,interaction: discord.Interaction,button:Button):
        self.responce="loop1"
        self.message_id=interaction.message.id
        if button.style==ButtonStyle.green:
            button.style=ButtonStyle.grey
        else:
            button.style=ButtonStyle.green
        await interaction.response.defer()
        
    @discord.ui.button(style = ButtonStyle.grey,emoji = '⏹',custom_id = "stop",row=1)
    async def button_callback6(self,interaction: discord.Interaction,button:Button):
        self.responce="stop"
        self.message_id=interaction.message.id
        await interaction.response.defer()
    

async def searc(ctx=Context):
    arg=ctx.message.content.split('%play')
    arg=arg[-1]
    non='True'
    if "playlist" in arg:
        non='False'
    YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist':'True'}
    with YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            request.get(arg) 
        except:
            
            vide = ydl.extract_info(f"ytsearch:{arg}", download=False)
        else:
            vide = ydl.extract_info(arg, download=False)
        for video in vide['entries']:
            for property in ['webpage_url']:
                url=video.get(property)
    return url

@bot.command()
async def play(ct=Context, url=str()):
    id = ct.message.guild.id
    try:
        channel = ct.message.author.voice.channel
    except:
        await log("WARNING "+str(traceback.format_exc()))
        await ct.send("Подключитесь к голосовому каналу")
        return
    voice = get(bot.voice_clients, guild=ct.guild)
    voice_client = ct.message.guild.voice_client
    chk=False
    for i in range(len(songsqueue)):
        if songsqueue[i][3]==id:
            chk=True
            id=i
            break
    if chk==False:
        s1=asyncio.Queue()
        s2=asyncio.Queue()
        s3=asyncio.LifoQueue()
        s4=asyncio.Queue()
        songsqueue.append([s1,s2,s3,id,s4])
        id=len(songsqueue)-1
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
                        await songsqueue[id][0].put(url)
                        await songsqueue[id][1].put(url)
                await ct.send("Playlist append to queue")
            else:
                await songsqueue[id][0].put(url)
                await songsqueue[id][1].put(url)
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    await ct.send(str(ydl.extract_info(url, download = False).get('title'))+" append to queue")
        else:
            url=(await searc(ct))
            await songsqueue[id][0].put(url)
            await songsqueue[id][1].put(url)
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                await ct.send(str(ydl.extract_info(url, download = False).get('title'))+" append to queue")
    await log("INFO server"+str(id))
    await log("INFO queue "+str(songsqueue))
    try: 
        if voice_client.is_playing() or voice_client.is_paused():
            return
    except:
        pass
    if songsqueue[id][0].empty():
        await ct.send("Список песен пуст")
        return
    await ct.send("Приготовтесь, проигрывание начнется скоро")
    try:
        voice = get(bot.voice_clients, guild=ct.guild)
        if voice and voice.is_connected():
            await voice.move_to(channel)
        else:
            voice = await channel.connect()
            await ct.send(f'Бот подключился к голосовому каналу: {channel}')
    except:
        await log("WARNING "+str(traceback.format_exc()))
        voice = get(bot.voice_clients, guild=ct.guild)
        if voice and voice.is_connected():
            await voice.move_to(channel)
        else:
            voice = await channel.connect()
            await ct.send(f'Бот подключился к голосовому каналу: {channel}')
    else:
        pass
    url= await songsqueue[id][0].get()
    url1=url
    await songsqueue[id][1].get()
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }],
    }
    name='Stop'
    if not songsqueue[id][1].empty():
        track=await songsqueue[id][1].get()
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            name = ydl.extract_info(track, download = False).get('title')
    else:
        name='Stop'
    
    FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 
                      'options': '-vn'}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download = False)#Берем музыку с Ютуба
    #Проверка на стрим
    if info['live_status']=="is_live":
        stream=True
        duration=0
    else:
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
    view=playerView(timeout=36000)
    msg=await ct.send(embed = 
    discord.Embed(
        title = '**C** - ' + info.get('title'),
        description="**Следующая песня:"+name+"     Песен в списке: "+str(songsqueue[id][0].qsize())+"**",
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
    await songsqueue[id][4].put(url)
    while voice_client.is_playing() or voice_client.is_paused() or not songsqueue[id][0].empty():#Пока очередь музыки не пуста или музыка проигрывается или стоит на паузе, проигрываем музыку и проверяем очередь
        await asyncio.sleep(1)
        if time.time()-msgtime>60*30:
            msgtime=time.time()
            await msg.delete()
            msg=await ct.send(
            embed = discord.Embed(title = '**Сейчас играет** - ' + info.get('title'),description="**Следующая песня:"+name+"     Песен в списке: "+str(songsqueue[id][0].qsize())+"**",color=0x0033ff),
            view=view)
            ID=msg.id
        if view.responce!='' and view.message_id==ID: #Проверка нажатия кнопки
            if view.responce == 'pla':#play pause
                if voice_client.is_playing():
                    voice_client.pause()
                elif voice_client.is_paused():
                    voice_client.resume()

            if view.responce =='back':#Перемотка на предыдущую песню
                if  songsqueue[id][2].empty():
                    pass
                else:
                    voice_client.stop()
                    tostart=asyncio.Queue()
                    while not songsqueue[id][0].empty():
                        await tostart.put(await songsqueue[id][0].get())
                    while not songsqueue[id][1].empty():
                        await songsqueue[id][1].get()
                    if not songsqueue[id][2].empty():
                        sus=await songsqueue[id][2].get()
                        await songsqueue[id][0].put(sus)
                        await songsqueue[id][0].put(url)
                        await songsqueue[id][1].put(url)
                    else:
                        await songsqueue[id][0].put(url)
                    while not tostart.empty():
                        sus=await tostart.get()
                        await songsqueue[id][0].put(sus)
                        await songsqueue[id][1].put(sus)
                    tostart=asyncio.Queue()
                    while songsqueue[id][4].qsize()>2:
                        await tostart.put(await songsqueue[id][4].get())
                    await songsqueue[id][4].get()
                    await songsqueue[id][4].get()
                    while not tostart.empty():
                        await songsqueue[id][4].put(await tostart.get())
                    url=0

            if view.responce=='skip':#Пропускаем песню с помощью команды стоп
                if voice_client.is_playing() or voice_client.is_paused():
                    voice_client.stop()
                else:
                    await ct.send("Бот не проигрывает ничего в данный момент")

            if view.responce =='stop':#Если нажали стоп то очищаем очередь и покидаем voice channel
                await voice_client.disconnect()
                while not songsqueue[id][0].empty():
                    url = await songsqueue[id][0].get()
                while not songsqueue[id][1].empty():
                    url = await songsqueue[id][1].get()
                while not songsqueue[id][2].empty():
                    url = await songsqueue[id][2].get()
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
            if songsqueue[id][0].empty() and loop==False and not(voice_client.is_playing() or voice_client.is_paused()):
                if loopplay==True:
                    await songsqueue[id][0].put(await songsqueue[id][4].get())
                    while not songsqueue[id][4].empty():
                        loo=await songsqueue[id][4].get()
                        await songsqueue[id][1].put(loo)
                        await songsqueue[id][0].put(loo)
                    while not songsqueue[id][2].empty():
                        await songsqueue[id][2].get()
                else:
                    await ct.send('Список песен пуст')
                    break
            else:
                try:
                    if loop==False:#Если зацикливание выключено берем песню из очереди, если включено воспроизводим туже
                        if url!=0:
                            await songsqueue[id][2].put(url)
                        if songsqueue[id][0].qsize()==songsqueue[id][1].qsize():
                            await songsqueue[id][1].get()
                        url=await songsqueue[id][0].get()
                        await songsqueue[id][4].put(url)
                        name='Stop'
                        if loopplay==True and songsqueue[id][1].empty():
                            name = ydl.extract_info(url1, download = False).get('title')
                        if not songsqueue[id][1].empty():#Берем название следующей песни для проигрывателя, если очередь пуста пишем stop
                            track=await songsqueue[id][1].get()
                            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                                name = ydl.extract_info(track, download = False).get('title')
                        prev=""
                        if not songsqueue[id][2].empty():#Берем название следующей песни для проигрывателя, если очередь пуста пишем stop
                            trac=await songsqueue[id][2].get()
                            await songsqueue[id][2].put(trac)
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
            embed = discord.Embed(title = '**Сейчас играет** - ' + info.get('title')+'\n'+st,description="**Следующая песня: "+name+'\n'+"     Песен в списке: "+str(songsqueue[id][0].qsize())+"**"+'\n'+"**Предыдущая песня: "+prev+"**",color=0x0033ff),view=view)
        else:
            await msg.edit(
            embed = discord.Embed(title = '**Сейчас играет** - ' + info.get('title')+'\n'+"**STREAM**",description="**Следующая песня: "+name+'\n'+"     Песен в списке: "+str(songsqueue[id][0].qsize())+"**"+'\n'+"**Предыдущая песня: "+prev+"**",color=0x0033ff),view=view)
    try:
        await ct.voice_client.disconnect()
    except:
        await log("WARNING "+str(traceback.format_exc()))
        pass
#Пропуск трека
@bot.command()
async def skip(ctx=Context):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()
    else:
        await ctx.send("Бот ничего не проигрывает в данный момент")
#Паузв
@bot.command()
async def pause(ctx=Context):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        voice_client.pause()
    else:
        await ctx.send("Бот ничего не проигрывает в данный момент")
#Продолжть воспроизведение
@bot.command()
async def resume(ctx=Context):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        voice_client.resume()
    else:
        await ctx.send("Бот ничего не проигрывал до этого. Используйте %play команду")
@bot.command()
async def join(ctx=Context):
    global voice

    channel = ctx.message.author.voice.channel
    voice = get(bot.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(channel)
    else:
        voice = await channel.connect()
        await ctx.send(f'Бот присоединился к голосовому чату: {channel}')
#Отключение
@bot.command()
async def leave(ctx=Context):
    await ctx.voice_client.disconnect()

#МЕМЫ
@bot.command()
async def support(ctx=Context):
    embed=discord.Embed(title="Support",description="https://donatty.com/liveisfpv",url="https://donatty.com/liveisfpv", color=0x0033ff)
    r = requests.get("https://api.waifu.pics/sfw/"+"hug")
    #print(r.json())
    imageurl=r.json()["url"]
    embed.set_image(url=imageurl)
    await ctx.send(embed=embed)


@bot.command()
async def animeme(ctx=Context):
    async with asyncpraw.Reddit(client_id=reddit_api['client_id'],
                     client_secret=reddit_api['client_secret'],
                     user_agent=reddit_api['user_agent'],
                     ) as reddit:
        meme_subreddit = await reddit.subreddit('Animemes')
        memes_submissions = meme_subreddit.hot(limit=100)
        memes_all=[]
        async for submission in memes_submissions:
            memes_all.append(submission)
        submission=random.choice(memes_all)
        pov=0
        while True and pov<1000:
            pov+=1
            if ".jpg" in submission.url or ".png" in submission.url or ".gif" in submission.url:
                break
            submission=random.choice(memes_all)
        title = translate.translate(text=submission.title,dest='ru')
        embed = discord.Embed(title=submission.title +"\n"+title.text)
        embed.set_image(url=submission.url)
        await ctx.send(embed=embed)

@bot.command()
async def loli(ctx=Context):
    memes_all=[]
    async with asyncpraw.Reddit(client_id=reddit_api['client_id'],
                     client_secret=reddit_api['client_secret'],
                     user_agent=reddit_api['user_agent'],
                     ) as reddit:
        meme_subreddit = await reddit.subreddit('Lolirefugees')
        memes_submissions = meme_subreddit.hot(limit=50)
        async for submission in memes_submissions:
            memes_all.append(submission)
        submission=random.choice(memes_all)
        pov=0
        while True and pov<1000:
            pov+=1
            if ".jpg" in submission.url or ".png" in submission.url or ".gif" in submission.url:
                break
            submission=random.choice(memes_all)
        title = translate.translate(text=submission.title,dest='ru')
        embed = discord.Embed(title=submission.title +"\n"+title.text)
        embed.set_image(url=submission.url)
        await ctx.send(embed=embed)
        if random.randint(0,1)==1:
            await asyncio.sleep(5)
            embed=discord.Embed(title="CALL FBI")
            embed.set_image(url = "https://static.life.ru/publications/2021/0/7/647334249696.4198.gif")
            await ctx.send(embed=embed)
            await asyncio.sleep(2)
            embed=discord.Embed(title="FBI SO CLOSE")
            embed.set_image(url = "https://i.gifer.com/origin/b3/b3d55ae5d60049304d0bd8a4619efa59.gif")
            await ctx.send(embed=embed)
            await asyncio.sleep(1)
            embed=discord.Embed(title="FBI OPEN UP")
            embed.set_image(url = "https://c.tenor.com/_YqdfwYLiQ4AAAAC/traffic-fbi-open-up.gif")
            await ctx.send(embed=embed)

@bot.command()
async def meme(ctx=Context):
    async with asyncpraw.Reddit(client_id=reddit_api['client_id'],
                     client_secret=reddit_api['client_secret'],
                     user_agent=reddit_api['user_agent'],
                     ) as reddit:
        meme_subreddit = await reddit.subreddit('memes')
        memes_submissions = meme_subreddit.hot(limit=100)
        memes_all=[]
        async for submission in memes_submissions:
            memes_all.append(submission)
        submission=random.choice(memes_all)
        pov=0
        while True and pov<1000:
            pov+=1
            if ".jpg" in submission.url or ".png" in submission.url or ".gif" in submission.url:
                break
            submission=random.choice(memes_all)
        title = translate.translate(text=submission.title,dest='ru')
        embed = discord.Embed(title=submission.title +"\n"+title.text)
        embed.set_image(url=submission.url)
        await ctx.send(embed=embed)

@bot.command()
async def Reddit(ctx=Context,name=str()):
    async with asyncpraw.Reddit(client_id=reddit_api['client_id'],
                     client_secret=reddit_api['client_secret'],
                     user_agent=reddit_api['user_agent'],
                     ) as reddit:
        mas18=['hentai','bondage','nsfw','xxx','18+','porn','fuck','shit']
        chose=''
        async for submission in  reddit.subreddits.search_by_name(name, False,False):
            nsfw=False
            for shit in mas18:
                if shit in str(submission).lower():
                    nsfw=True
                    break
            if nsfw==False:
                if chose=='':
                    chose+=str(submission)
                else:
                    chose+='+'
                    chose+=str(submission)
        print(chose)
        if True:
            await ctx.send("Рандомно выбраны мемы из: "+chose.replace('+',', '))
            meme_subreddit = await reddit.subreddit(str(chose))
            memes_submissions = meme_subreddit.hot(limit=25*chose.count('+') )
            memes_all=[]
            async for submission in memes_submissions:
                memes_all.append(submission)
            submission=random.choice(memes_all)
            pov=0
            while True and pov<250*chose.count('+'):
                pov+=1
                print(submission.url)
                if not submission.over_18:
                    if ".jpg" in submission.url or ".png" in submission.url or ".gif" in submission.url or "youtu" in submission.url:
                        break
                submission=random.choice(memes_all)
            if submission.over_18:
                await ctx.send("Subreddit:"+name+" Не найден")
                return
            else:
                title = translate.translate(text=submission.title,dest='ru')
                if len(str(title.text)+str(submission.title))<256:
                    embed = discord.Embed(title=submission.title +"\n"+title.text)
                else:
                    embed = discord.Embed(title=submission.title)
                if pov<250*chose.count('+') and(".jpg" in submission.url or ".png" in submission.url or ".gif" in submission.url):
                    embed.set_image(url=submission.url)
                    await ctx.send(embed=embed)
                else:
                    if len(str(title.text)+str(submission.title))<256:
                        embed = discord.Embed(title=submission.title +"\n"+title.text,color=0xe74c3c)
                    else:
                        embed = discord.Embed(title=submission.title,color=0xe74c3c)
                    await ctx.send(embed=embed)
                    await ctx.send(submission.url)

@bot.command()
async def genshin(ctx=Context):
    async with asyncpraw.Reddit(client_id=reddit_api['client_id'],
                     client_secret=reddit_api['client_secret'],
                     user_agent=reddit_api['user_agent'],
                     ) as reddit:
        meme_subreddit = await reddit.subreddit('Genshin_Memepact')
        memes_submissions = meme_subreddit.hot(limit=100)
        memes_all=[]
        async for submission in memes_submissions:
            memes_all.append(submission)
        submission=random.choice(memes_all)
        pov=0
        while True and pov<1000:
            pov+=1
            if ".jpg" in submission.url or ".png" in submission.url or ".gif" in submission.url:
                break
            submission=random.choice(memes_all)
        title = translate.translate(text=submission.title,dest='ru')
        embed = discord.Embed(title=submission.title +"\n"+title.text)
        embed.set_image(url=submission.url)
        await ctx.send(embed=embed)

@bot.command()
async def potato(ctx=Context):
    async with asyncpraw.Reddit(client_id=reddit_api['client_id'],
                     client_secret=reddit_api['client_secret'],
                     user_agent=reddit_api['user_agent'],
                     ) as reddit:
        meme_subreddit = await reddit.subreddit('potato')
        memes_submissions = meme_subreddit.hot(limit=100)
        memes_all=[]
        async for submission in memes_submissions:
            memes_all.append(submission)
        submission=random.choice(memes_all)
        pov=0
        while True and pov<1000:
            pov+=1
            if ".jpg" in submission.url or ".png" in submission.url or ".gif" in submission.url:
                break
            submission=random.choice(memes_all)
        title = translate.translate(text=submission.title,dest='ru')
        embed = discord.Embed(title=submission.title +"\n"+title.text)
        embed.set_image(url=submission.url)
        await ctx.send(embed=embed)

#ПИКАПИКАЧУ
@bot.command()
async def pikachu(ctx=Context):
    response = requests.get('https://some-random-api.ml/img/pikachu') # Get-запрос
    json_data = json.loads(response.text) # Извлекаем JSON

    embed = discord.Embed(color = 0xff9900, title = 'pikachu') # Создание Embed'a
    embed.set_image(url = json_data['link']) # Устанавливаем картинку Embed'a
    await ctx.send(embed = embed) # Отправляем Embed
#Аниме пацанский цитатник
@bot.command()
async def anime(ctx=Context):
    response = requests.get('https://some-random-api.ml/animu/quote') # Get-запрос
    json_data = json.loads(response.text) # Извлекаем JSON
    result = translate.translate(text=json_data["sentence"], src='en', dest='ru')
    await ctx.send(result.text+" Персонаж: "+json_data["character"]+" Аниме: "+json_data["anime"])
    #print(json_data)

@bot.command()
async def waifu(ctx=Context, *, waifu='waifu'):
    if waifu=='help':
        embed=discord.Embed(title="WAIFU commands list:", description="**waifu\nneko\nshinobu\nmegumin\nbully\ncuddle\ncry\nhug\nawoo\nkiss\nlick\npat\nsmug\nbonk\nyeet\nblush\nsmile\nwave\nhighfive\nhandhold\nnom\nbite\nglomp\nslap\nkill\nkick\nhappy\nwink\npoke\ndance\ncringe**",color=0x0033ff)
        r = requests.get("https://api.waifu.pics/sfw/"+"waifu")
        #print(r.json())
        imageurl=r.json()["url"]
        embed.set_image(url=imageurl)
        await ctx.send(embed=embed)
    else:
        r = requests.get("https://api.waifu.pics/sfw/"+waifu)
        #print(r.json())
        imageurl=r.json()["url"]
        embed=discord.Embed(title=waifu,color=0x0033ff)
        embed.set_image(url=imageurl)
        await ctx.send(embed=embed)

requesttime=time.time()
@bot.command()
async def c(ctx=Context, *, query="naruto"):
    global requesttime
    query=query.title().lower()
    #print(query)
    if time.time()-requesttime<1.5:
        asyncio.sleep(time.time()-requesttime)
        requesttime=time.time()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36"}
    try:
        reqcont = requests.get("https://www.animecharactersdatabase.com/api_series_characters.php?character_q="+query,headers=headers)
        #print(reqcont.json())
        if reqcont.content==-1 or reqcont.content=='-1': # i found out that the website returns: -1 if there are no results, so here, we implement it
            await ctx.send("[-] Unable to find results! - No such results exists!")

        else:
            # If the website doesnt return: -1 , this will happen
            try:
                reqcont = reqcont.json()
            except Exception as e:

                # Please enable this line only while you are developing and not when deplying
                await ctx.send(reqcont.content)

                await ctx.send(f"[-] Unable to turn the data to json format! {e}")
                return # the function will end if an error happens in creating a json out of the request

            # selecting a random item for the output
            cur_info=[]
            for curent_info in reqcont["search_results"]:
                
                #rand_val = len(reqcont["search_results"])-1
                #get_index = random.randint(0, rand_val)
                #curent_info = reqcont["search_results"][get_index]

                # Creting the embed and sending it

                if query in [i.lower() for i in list(curent_info['name'].split())]:
                    cur_info.append(curent_info)
                    #embed=discord.Embed(title="Anime Info", description=f":smiley: Anime Character Info result for {query}", color=0x00f549)
                    #embed.set_author(name="Картошка", icon_url="https://cdn.discordapp.com/attachments/877796755234783273/879295069834850324/Avatar.png")
                    #embed.set_thumbnail(url=f"{curent_info['anime_image']}")
                    #embed.set_image(url=f"{curent_info['character_image']}")
                    #embed.add_field(name="Anime Name", value=f"{curent_info['anime_name']}", inline=False)
                    #embed.add_field(name="Name", value=f"{curent_info['name']}", inline=False)
                    #embed.add_field(name="Gender", value=f"{curent_info['gender']}", inline=False)
                    #embed.add_field(name="Description", value=f"{curent_info['desc']}", inline=False)
                    #await ctx.send(embed=embed)
            if len(cur_info)==0:
                rand_val = len(reqcont["search_results"])-1
                get_index = random.randint(0, rand_val)
                curent_info = reqcont["search_results"][get_index]
            elif len(cur_info)==1:
                get_index=0
                curent_info = cur_info[get_index]
            else:
                rand_val = len(cur_info)-1
                get_index = random.randint(0, rand_val)
                curent_info = cur_info[get_index]
            embed=discord.Embed(title="Информация об аниме", description=f":smiley: Информация об аниме персонаже {query}", color=0x00f549)
            embed.set_author(name="NEKO", icon_url=bot.user.avatar.url)
            embed.set_thumbnail(url=f"{curent_info['anime_image']}")
            embed.set_image(url=f"{curent_info['character_image']}")
            embed.add_field(name="Название аниме", value=f"{curent_info['anime_name']}", inline=False)
            embed.add_field(name="Имя", value=f"{curent_info['name']}", inline=False)
            embed.add_field(name="Пол", value=f"{curent_info['gender']}", inline=False)
            embed.add_field(name="Описание", value=f"{curent_info['desc']}", inline=False)
            await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"[-] An error has occured: {e}")

    
#For creator ONLY
@bot.command()
async def lev(ctx=Context):
    if ctx.message.author.id ==395466697626353665:
        await ctx.message.guild.leave()
        await log("INFO Leave "+str(ctx.message.guild.id))

@bot.event
async def on_message(message):
    await bot.process_commands(message)
#Приветствие нового члена в выбранном чате
@bot.event
async def on_member_join(member):
    embed=discord.Embed(title="Welcome to the club buddy!", description=f"К нам в {member.guild.name} приехал {member.mention}!", color=0xCC974F) #Embed
    embed.set_image(url = "https://c.tenor.com/i27B-Xj0CSQAAAAd/welcome-to-the-club-buddy-butt-slap.gif")
    await member.send(embed=embed) #Отправка сообщения
    embed=discord.Embed(title="NEKO bot lite commands:", description=f"""**%version**-Версия бота и описание последнего обновления
        **%pikachu**- Отправляет рандомного пикачу
        **%Reddit 'Название группы'**-Отправляет рандомный пост из этой группы
        **%anime**-Выводит рандомную аниме цитату
        **%meme**- Рандомный популярный мем
        **%potato**- КАРТОШКА
        **%genshin**-Все для геншинфагов
        **%animeme**-Анимешные мемы тоже в чате
        **%trans**- Для свободного взаимодействия
        **%loli-Используйте эту команду только в том случае, если хотите сесть в тюрьму на 8 лет, но 8 лет – не срок…**
        В полной версии автоматически переводит мемы
        В этой присутствуют мини игры
        **%FBI-FBI OPEN UP**
        **%c**-Найти аниме с этим персонажем
        **%waifu**-print **'%waifu help'** Чтобы увидеть список доступных для этой команд
        **%neko-NEKOCHAN!!!!!** Неко неко неко
        *%support*
        *Created by LiveisFPV*""", color=0x0033ff)
    embed.set_author(name="NEKO", icon_url=bot.user.avatar.url)
    r = requests.get("https://api.waifu.pics/sfw/"+"neko")
    #print(r.json())
    imageurl=r.json()["url"]
    embed.set_image(url=imageurl)
    await member.send(embed=embed)
    embed=discord.Embed(title="MUSIC commands:", description=f"""**%play**-Воспроизвести/добавить трек/плейлист или найти песню
        **%pause**-Поставить на паузу
        **%resume**-Продолжить
        **%skip**-Пропустить трек
        **Кнопки:
        Back
        Play/pause
        Skip
        Loop queue
        Stop and leave
        Loop track**""",color=0x0033ff)
    embed.set_image(url="https://images.pexels.com/photos/3104/black-and-white-music-headphones-life.jpg?auto=compress&cs=tinysrgb&dpr=2&h=750&w=1260")
    embed.set_author(name="NEKO", icon_url=bot.user.avatar.url)
    await member.send(embed=embed)
#Старт бота
@bot.event
async def on_ready():
    #print("Ready!")
    await log("INFO Bot started")
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("%help"))
    await status()
bot.run(settings['token'])