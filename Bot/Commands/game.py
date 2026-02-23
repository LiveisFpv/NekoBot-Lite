from Games.snake import Snake
from discord.ext.commands import Context
from discord.ext import commands

class GameCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @commands.hybrid_command(name='snake',help='Its snake game only')
    async def snake(self, ctx=Context,name="text"):
        view=Snake()
        if name!="text":
            file,embed=await view.get_image()
            msg = await ctx.send(file=file,embed=embed)
            while True:
                file,embed=await view.get_image()
                await msg.edit(embed=embed,attachments=[file],view=view)
        else:
            embed,over=await view.get_text()
            msg= await ctx.send(embed=embed,view=view)
            while not over:
                embed,over=await view.get_text()
                await msg.edit(embed=embed)
        view.stop()
        del view

async def setup(bot):
    await bot.add_cog(GameCommand(bot))