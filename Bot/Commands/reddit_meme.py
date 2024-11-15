from discord.ext.commands import Context
from discord.ext import commands
from Reddit.async_praw import get_reddit_instance
import random
import discord
import asyncio

class RedditMemeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(name='animeme')
    async def animeme(self,ctx=Context):
        reddit=await get_reddit_instance()
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
        embed = discord.Embed(title=submission.title)
        embed.set_image(url=submission.url)
        await ctx.send(embed=embed)

    @commands.command(name='loli')
    async def loli(self,ctx=Context):
        memes_all=[]
        reddit=await get_reddit_instance()
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
        embed = discord.Embed(title=submission.title)
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

    @commands.command(name='meme')
    async def meme(self,ctx=Context):
        reddit=await get_reddit_instance()
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
        embed = discord.Embed(title=submission.title)
        embed.set_image(url=submission.url)
        await ctx.send(embed=embed)

    @commands.command(naem="Reddit")
    async def Reddit(self,ctx=Context,name=str()):
        reddit=await get_reddit_instance()
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

    @commands.command(name='genshin')
    async def genshin(self,ctx=Context):
        reddit=await get_reddit_instance()
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
        embed = discord.Embed(title=submission.title)
        embed.set_image(url=submission.url)
        await ctx.send(embed=embed)

    @commands.command(name='potato')
    async def potato(self,ctx=Context):
        reddit=await get_reddit_instance()
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
        embed = discord.Embed(title=submission.title)
        embed.set_image(url=submission.url)
        await ctx.send(embed=embed)

    
async def setup(bot):
    await bot.add_cog(RedditMemeCommands(bot))