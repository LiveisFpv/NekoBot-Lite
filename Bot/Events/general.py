from discord.ext import commands
from utils.utils import log
import discord
class EventHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    #Старт бота
    @commands.Cog.listener()
    async def on_ready(self):
        #print("Ready!")
        await log("INFO Bot started")
        await self.bot.change_presence(status=discord.Status.online, activity=discord.Game("%help"))

    # Приветствие нового члена 
    @commands.Cog.listener()
    async def on_member_join(self,member):
        embed=discord.Embed(title="Welcome to the club buddy!", description=f"К нам в {member.guild.name} приехал {member.mention}!", color=0xCC974F) #Embed
        embed.set_image(url = "https://c.tenor.com/i27B-Xj0CSQAAAAd/welcome-to-the-club-buddy-butt-slap.gif")
        await member.send(embed=embed) #Отправка сообщения
        embed=discord.Embed(title="NEKO bot lite commands:", description=open("./Bot/md/help.md",encoding="utf-8").read(), color=0x0033ff)
        embed.set_author(name="NEKO", icon_url=self.bot.user.avatar.url)
        # r = requests.get("https://api.waifu.pics/sfw/"+"neko")
        # #print(r.json())
        # imageurl=r.json()["url"]
        # embed.set_image(url=imageurl)
        await member.send(embed=embed)
        embed=discord.Embed(title="MUSIC commands:", description=open("./Bot/md/play_help.md",encoding="utf-8").read(),color=0x0033ff)
        embed.set_image(url="https://images.pexels.com/photos/3104/black-and-white-music-headphones-life.jpg?auto=compress&cs=tinysrgb&dpr=2&h=750&w=1260")
        embed.set_author(name="NEKO", icon_url=self.bot.user.avatar.url)
        await member.send(embed=embed)


async def setup(bot):
    await bot.add_cog(EventHandler(bot))
