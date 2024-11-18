from discord.ext.commands import Context
from discord.ext import commands
import discord
import requests
from googletrans import Translator
from Utils.utils import log

# Define your cog here. This will be the main entry point for your bot's commands.
class GeneralCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='ping', help='Check if the bot is online')
    async def ping(self, ctx: Context):
        latency = self.bot.latency
        await ctx.send(f'Pong! {latency}s')
    
    @commands.command(name='version', help='Check bot version')
    async def version(self,ctx=Context): 
        embed=discord.Embed(title="NEKO bot lite Версия 1.5 Бета:", description=open("./Bot/md/update.md",encoding='utf-8').read(), color=0x0033ff)
        # r = requests.get("https://api.waifu.pics/sfw/"+"neko")
        # imageurl=r.json()["url"]
        # # embed.set_image(url=imageurl)
        await ctx.send(embed=embed)
    
    @commands.command(name='help',help='Show help information')
    async def help(self,ctx=Context):
        
        embed=discord.Embed(title="NEKO bot lite commands:", description=open("./Bot/md/help.md",encoding="utf-8").read(), color=0x0033ff)
        embed.set_author(name="NEKO", icon_url=self.bot.user.avatar.url)
        # r = requests.get("https://api.waifu.pics/sfw/"+"neko")
        # imageurl=r.json()["url"]
        # embed.set_image(url=imageurl)
        await ctx.send(embed=embed)
        embed=discord.Embed(title="MUSIC commands:", description=open("./Bot/md/play_help.md",encoding="utf-8").read(),color=0x0033ff)
        embed.set_author(name="NEKO", icon_url=self.bot.user.avatar.url)
        embed.set_image(url="https://images.pexels.com/photos/3104/black-and-white-music-headphones-life.jpg?auto=compress&cs=tinysrgb&dpr=2&h=750&w=1260")
        await ctx.send(embed=embed)

    @commands.command(name='support',help='Show support information')
    async def support(self, ctx=Context):
        embed=discord.Embed(title="Support",description="https://donatty.com/liveisfpv",url="https://donatty.com/liveisfpv", color=0x0033ff)
        r = requests.get("https://api.waifu.pics/sfw/"+"hug")
        #print(r.json())
        imageurl=r.json()["url"]
        embed.set_image(url=imageurl)
        await ctx.send(embed=embed)
    
    @commands.command(name='trans',help='Translate text')
    async def trans(self,ctx=Context):
        translate=Translator()
        sr=ctx.message.content.split("%trans")
        stre=str()
        for i in sr:
            stre+=i
        result = translate.translate(text=stre,dest='ru')
        await ctx.send(result.text)

    @commands.command(name='lev')
    async def lev(self,ctx=Context):
        if ctx.message.author.id ==395466697626353665:
            await ctx.message.guild.leave()
            await log("INFO Leave "+str(ctx.message.guild.id))
        
async def setup(bot):
    await bot.add_cog(GeneralCommands(bot))