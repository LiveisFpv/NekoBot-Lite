from discord.ext import commands
from discord.ext.commands import Context
import discord

from services.generalService import GeneralService
from utils.utils import log


class GeneralCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.general_service = GeneralService()

    @commands.command(name="ping", help="Check if the bot is online")
    async def ping(self, ctx: Context):
        latency = self.bot.latency
        await ctx.send(f"Pong! {latency}s")

    @commands.command(name="version", help="Check bot version")
    async def version(self, ctx=Context):
        embed = discord.Embed(
            title="NEKO-lite Версия 1.6",
            description=self.general_service.get_version_text(),
            color=0x0033FF,
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="help", help="Show help information")
    async def help(self, ctx=Context):
        avatar = getattr(getattr(self.bot, "user", None), "avatar", None)
        avatar_url = avatar.url if avatar else None

        base_embed = discord.Embed(
            title="NEKO-lite commands:",
            description=self.general_service.get_help_text(),
            color=0x0033FF,
        )
        if avatar_url:
            base_embed.set_author(name="NEKO", icon_url=avatar_url)
        await ctx.send(embed=base_embed)

        music_embed = discord.Embed(
            title="MUSIC commands:",
            description=self.general_service.get_music_help_text(),
            color=0x0033FF,
        )
        if avatar_url:
            music_embed.set_author(name="NEKO", icon_url=avatar_url)
        music_embed.set_image(
            url="https://images.pexels.com/photos/3104/black-and-white-music-headphones-life.jpg?auto=compress&cs=tinysrgb&dpr=2&h=750&w=1260"
        )
        await ctx.send(embed=music_embed)

    @commands.command(name="support", help="Show support information")
    async def support(self, ctx=Context):
        embed = discord.Embed(
            title="Support",
            description="https://donatty.com/liveisfpv",
            url="https://donatty.com/liveisfpv",
            color=0x0033FF,
        )
        try:
            image_url = await self.general_service.get_support_image_url()
            if image_url:
                embed.set_image(url=image_url)
        except Exception:
            # Keep command available even when external API is unavailable.
            pass
        await ctx.send(embed=embed)

    @commands.command(name="tran", help="Translate text")
    async def tran(self, ctx=Context):
        parts = ctx.message.content.split(maxsplit=1)
        raw_text = parts[1] if len(parts) > 1 else ""
        if not raw_text.strip():
            await ctx.send("Введите текст после команды.")
            return

        try:
            translated = await self.general_service.translate_to_ru(raw_text)
        except Exception:
            await ctx.send("Не удалось перевести текст.")
            return

        await ctx.send(translated)

    @commands.command(name="lev")
    async def lev(self, ctx=Context):
        if ctx.message.author.id == 395466697626353665:
            await ctx.message.guild.leave()
            await log("INFO Leave " + str(ctx.message.guild.id))


async def setup(bot):
    await bot.add_cog(GeneralCommands(bot))
