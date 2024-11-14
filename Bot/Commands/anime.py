from discord.ext.commands import Context
from discord.ext import commands
import time
import asyncio
import requests
import random
import discord

class AnimeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @commands.command(name='c',help='Search anime person in DB')
    async def c(self,ctx=Context, *, query="naruto"):
        requesttime=time.time()
        query=query.title().lower()
        #print(query)
        if time.time()-requesttime<1.5:
            asyncio.sleep(time.time()-requesttime)
            requesttime=time.time()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36"}
        try:
            reqcont = requests.get("https://www.animecharactersdatabase.com/api_series_characters.php?character_q="+query,headers=headers)
            #print(reqcont.json())
            if reqcont.content==-1 or reqcont.content=='-1': # i found out that the website returns: -1 if there are no results, so here, we implement it
                await ctx.send("[-] Unable to find results! - No such results exists!")

            else:
                # If the website doesnt return: -1 , this will happen
                try:
                    reqcont = reqcont.json()
                except Exception as e:

                    # Please enable this line only while you are developing and not when deplying
                    await ctx.send(reqcont.content)

                    await ctx.send(f"[-] Unable to turn the data to json format! {e}")
                    return # the function will end if an error happens in creating a json out of the request

                # selecting a random item for the output
                cur_info=[]
                for curent_info in reqcont["search_results"]:
                    
                    #rand_val = len(reqcont["search_results"])-1
                    #get_index = random.randint(0, rand_val)
                    #curent_info = reqcont["search_results"][get_index]

                    # Creting the embed and sending it

                    if query in [i.lower() for i in list(curent_info['name'].split())]:
                        cur_info.append(curent_info)
                        #embed=discord.Embed(title="Anime Info", description=f":smiley: Anime Character Info result for {query}", color=0x00f549)
                        #embed.set_author(name="Картошка", icon_url="https://cdn.discordapp.com/attachments/877796755234783273/879295069834850324/Avatar.png")
                        #embed.set_thumbnail(url=f"{curent_info['anime_image']}")
                        #embed.set_image(url=f"{curent_info['character_image']}")
                        #embed.add_field(name="Anime Name", value=f"{curent_info['anime_name']}", inline=False)
                        #embed.add_field(name="Name", value=f"{curent_info['name']}", inline=False)
                        #embed.add_field(name="Gender", value=f"{curent_info['gender']}", inline=False)
                        #embed.add_field(name="Description", value=f"{curent_info['desc']}", inline=False)
                        #await ctx.send(embed=embed)
                if len(cur_info)==0:
                    rand_val = len(reqcont["search_results"])-1
                    get_index = random.randint(0, rand_val)
                    curent_info = reqcont["search_results"][get_index]
                elif len(cur_info)==1:
                    get_index=0
                    curent_info = cur_info[get_index]
                else:
                    rand_val = len(cur_info)-1
                    get_index = random.randint(0, rand_val)
                    curent_info = cur_info[get_index]
                embed=discord.Embed(title="Информация об аниме", description=f":smiley: Информация об аниме персонаже {query}", color=0x00f549)
                embed.set_author(name="NEKO", icon_url=self.bot.user.avatar.url)
                embed.set_thumbnail(url=f"{curent_info['anime_image']}")
                embed.set_image(url=f"{curent_info['character_image']}")
                embed.add_field(name="Название аниме", value=f"{curent_info['anime_name']}", inline=False)
                embed.add_field(name="Имя", value=f"{curent_info['name']}", inline=False)
                embed.add_field(name="Пол", value=f"{curent_info['gender']}", inline=False)
                embed.add_field(name="Описание", value=f"{curent_info['desc']}", inline=False)
                await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"[-] An error has occured: {e}")

async def setup(bot):
    await bot.add_cog(AnimeCommands(bot))