from discord.ext import commands
from Config.config import settings_bot
import os
import discord


intents = discord.Intents.all()
bot = commands.Bot(command_prefix = settings_bot['prefix'],intents=intents,help_command=None)
async def load_extensions():
    for filename in os.listdir('./Bot/Commands'):
        if filename.endswith('.py'):
            await bot.load_extension(f'Commands.{filename[:-3]}')
    for filename in os.listdir('./Bot/Events'):
        if filename.endswith('.py'):
            await bot.load_extension(f'Events.{filename[:-3]}')
    

if __name__ == "__main__":
    bot.setup_hook=load_extensions
    bot.run(settings_bot['token'])