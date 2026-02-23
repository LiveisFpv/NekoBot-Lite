from discord.ext.commands import Context
from discord.ext import commands
from services.redditService import RedditService
import random
import discord
import asyncio

class RedditMemeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reddit_service = RedditService()

    async def send_random_subreddit_meme(self, ctx: Context, subreddit_name: str, limit: int = 100):
        submission = await self.reddit_service.get_random_media_submission(subreddit_name, limit=limit)
        if submission is None:
            await ctx.send("Не удалось найти подходящий пост, попробуйте позже.")
            return
        embed = discord.Embed(title=submission.title)
        embed.set_image(url=submission.url)
        await ctx.send(embed=embed)
        
    @commands.hybrid_command(name='animeme')
    async def animeme(self,ctx=Context):
        await self.send_random_subreddit_meme(ctx, "Animemes")

    @commands.hybrid_command(name='loli')
    async def loli(self,ctx=Context):
        await self.send_random_subreddit_meme(ctx, "Lolirefugees", limit=50)
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

    @commands.hybrid_command(name='meme')
    async def meme(self,ctx=Context):
        await self.send_random_subreddit_meme(ctx, "memes")

    @commands.hybrid_command(name="Reddit")
    async def Reddit(self,ctx=Context,name=str()):
        reddit = await self.reddit_service.get_reddit_instance()
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
                embed = discord.Embed(title=submission.title)
                if pov<250*chose.count('+') and(".jpg" in submission.url or ".png" in submission.url or ".gif" in submission.url):
                    embed.set_image(url=submission.url)
                    await ctx.send(embed=embed)
                else:
                    embed = discord.Embed(title=submission.title,color=0xe74c3c)
                    await ctx.send(embed=embed)
                    await ctx.send(submission.url)

    @commands.hybrid_command(name='genshin')
    async def genshin(self,ctx=Context):
        await self.send_random_subreddit_meme(ctx, "Genshin_Memepact")

    @commands.hybrid_command(name='potato')
    async def potato(self,ctx=Context):
        await self.send_random_subreddit_meme(ctx, "potato")

    
async def setup(bot):
    await bot.add_cog(RedditMemeCommands(bot))
