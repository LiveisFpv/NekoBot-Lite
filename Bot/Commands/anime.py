from discord.ext import commands
from discord.ext.commands import Context
import discord

from services.animeService import AnimeService


class AnimeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.anime_service = AnimeService()

    @commands.command(name="c", help="Search anime person in DB")
    async def c(self, ctx=Context, *, query="naruto"):
        try:
            character = await self.anime_service.find_character(query)
        except Exception as error:
            await ctx.send(f"[-] An error has occured: {error}")
            return

        if character is None:
            await ctx.send("[-] Unable to find results! - No such results exists!")
            return

        embed = discord.Embed(
            title="Информация об аниме",
            description=f":smiley: Информация об аниме персонаже {query}",
            color=0x00F549,
        )
        avatar = getattr(getattr(self.bot, "user", None), "avatar", None)
        avatar_url = avatar.url if avatar else None
        if avatar_url:
            embed.set_author(name="NEKO", icon_url=avatar_url)
        embed.set_thumbnail(url=character.get("anime_image", ""))
        embed.set_image(url=character.get("character_image", ""))
        embed.add_field(name="Название аниме", value=character.get("anime_name", "unknown"), inline=False)
        embed.add_field(name="Имя", value=character.get("name", "unknown"), inline=False)
        embed.add_field(name="Пол", value=character.get("gender", "unknown"), inline=False)
        embed.add_field(name="Описание", value=character.get("desc", "unknown"), inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(AnimeCommands(bot))
