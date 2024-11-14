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
#MUSIC


    






#МЕМЫ



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
    embed=discord.Embed(title="NEKO bot lite commands:", description=open("help.md",encoding="utf-8").read(), color=0x0033ff)
    embed.set_author(name="NEKO", icon_url=bot.user.avatar.url)
    # r = requests.get("https://api.waifu.pics/sfw/"+"neko")
    # #print(r.json())
    # imageurl=r.json()["url"]
    # embed.set_image(url=imageurl)
    await member.send(embed=embed)
    embed=discord.Embed(title="MUSIC commands:", description=open("play_help.md",encoding="utf-8").read(),color=0x0033ff)
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