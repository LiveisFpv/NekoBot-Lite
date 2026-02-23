import asyncio

import discord
from discord.ext import commands
from discord.ext.commands import Context

from services.memeService import MemeService


class MemeCommands(commands.Cog):
    WAIFU_HELP_TEXT = (
        "**waifu\nneko\nshinobu\nmegumin\nbully\ncuddle\ncry\nhug\nawoo\nkiss\nlick\npat\nsmug\n"
        "bonk\nyeet\nblush\nsmile\nwave\nhighfive\nhandhold\nnom\nbite\nglomp\nslap\nkill\nkick\n"
        "happy\nwink\npoke\ndance\ncringe**"
    )

    def __init__(self, bot):
        self.bot = bot
        self.meme_service = MemeService()

    @commands.hybrid_command(name="FBI", help="CALL FBI if unlegal material")
    async def FBI(self, ctx=Context):
        embed = discord.Embed(title="CALL FBI")
        embed.set_image(url="https://static.life.ru/publications/2021/0/7/647334249696.4198.gif")
        await ctx.send(embed=embed)
        await asyncio.sleep(5)

        embed = discord.Embed(title="FBI SO CLOSE")
        embed.set_image(url="https://i.gifer.com/origin/b3/b3d55ae5d60049304d0bd8a4619efa59.gif")
        await ctx.send(embed=embed)
        await asyncio.sleep(5)

        embed = discord.Embed(title="FBI OPEN UP")
        embed.set_image(url="https://c.tenor.com/_YqdfwYLiQ4AAAAC/traffic-fbi-open-up.gif")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="anime")
    async def anime(self, ctx=Context):
        try:
            quote = await self.meme_service.get_anime_quote()
            sentence = quote["data"]["content"]
            character = quote["data"]["character"]["name"]
            anime_title = quote["data"]["anime"]["name"]
        except Exception:
            await ctx.send("Не удалось получить цитату, попробуйте позже.")
            return
        await ctx.send(f"{sentence}\nПерсонаж: {character}\nАниме: {anime_title}")

    @commands.hybrid_command(name="pikachu")
    async def pikachu(self, ctx=Context):
        try:
            image_url = await self.meme_service.get_pikachu_image_url()
        except Exception:
            await ctx.send("Не удалось загрузить изображение.")
            return

        if not image_url:
            await ctx.send("Изображение не найдено.")
            return

        embed = discord.Embed(color=0xFF9900, title="pikachu")
        embed.set_image(url=image_url)
        await ctx.send(embed=embed)

    @commands.hybrid_command("waifu")
    async def waifu(self, ctx=Context, *, waifu="waifu"):
        target = "waifu" if waifu == "help" else waifu
        try:
            image_url = await self.meme_service.get_waifu_image_url(target)
        except Exception:
            await ctx.send("Не удалось получить изображение.")
            return

        if waifu == "help":
            embed = discord.Embed(
                title="WAIFU commands list:",
                description=self.WAIFU_HELP_TEXT,
                color=0x0033FF,
            )
        else:
            embed = discord.Embed(title=waifu, color=0x0033FF)

        if image_url:
            embed.set_image(url=image_url)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(MemeCommands(bot))
