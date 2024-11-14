from discord.ext.commands import Context
from discord.ext import commands

class AnimeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    await bot.add_cog(AnimeCommands(bot))