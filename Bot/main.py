from discord.ext import commands
import json
import os
import discord
import asyncio

settings = json.load(open("./Bot/Config/bot.json","r"))
intents = discord.Intents.all()
bot = commands.Bot(command_prefix = settings['prefix'],intents=intents,help_command=None)
async def load_extensions():
    for filename in os.listdir('./Bot/Commands'):
        if filename.endswith('.py'):
            await bot.load_extension(f'Commands.{filename[:-3]}')
async def main():
    await load_extensions()
    

asyncio.run(main())
bot.run(settings['token'])