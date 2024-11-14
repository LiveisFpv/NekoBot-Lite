from discord.ext.commands import Context
from discord.ext import commands
import discord
import asyncio
import json
import requests
from googletrans import Translator

class MemeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command(name='FBI', help='CALL FBI if unlegal material')
    async def FBI(self,ctx=Context):
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
    
    #Аниме пацанский цитатник
    @commands.command(name='anime')
    async def anime(self,ctx=Context):
        translate=Translator()
        response = requests.get('https://some-random-api.ml/animu/quote') # Get-запрос
        json_data = json.loads(response.text) # Извлекаем JSON
        result = translate.translate(text=json_data["sentence"], src='en', dest='ru')
        await ctx.send(result.text+" Персонаж: "+json_data["character"]+" Аниме: "+json_data["anime"])
        #print(json_data)

    @commands.command(name='pikachu')
    async def pikachu(self,ctx=Context):
        response = requests.get('https://some-random-api.ml/img/pikachu')
        json_data = json.loads(response.text) # Извлекаем JSON

        embed = discord.Embed(color = 0xff9900, title = 'pikachu') # Создание Embed'a
        embed.set_image(url = json_data['link']) # Устанавливаем картинку Embed'a
        await ctx.send(embed = embed) # Отправляем Embed

    @commands.command('waifu')
    async def waifu(self, ctx=Context, *, waifu='waifu'):
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
async def setup(bot):
    await bot.add_cog(MemeCommands(bot))