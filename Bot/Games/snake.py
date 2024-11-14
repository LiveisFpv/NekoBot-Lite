import io
from discord.ui import Button, View
import discord
from discord import ButtonStyle
from PIL import Image, ImageDraw
import random
import asyncio

class Snake(View):
    def __init__(self):
        super().__init__(timeout=36000)
        self.goto="R"
        self.matrix=[["◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️"] for i in range(12)]
        self.coords=[[0,0],[1,0],[2,0]]
        self.apple=[2,2]
        self.image=Image.new('RGB',(240,240),'black')
        self.embed=discord.Embed(title="Snake game")
        self.score=0
        self.gameover=0
        with io.BytesIO() as image_binary:
                self.image.save(image_binary,"PNG")
                image_binary.seek(0)
                self.file=discord.File(fp=image_binary, filename='image.png')
    async def apple_update(self):
        check=0
        while self.apple in self.coords:
            self.apple=[(random.randint(0,11)),(random.randint(0,11))]
            check=1
        return check
    async def snake_update(self):
        check=0
        if self.goto=="R":
            if self.coords[-1][0]+1>=12 or [self.coords[-1][0]+1,self.coords[-1][1]] in self.coords:
                self.gameover=1
            else:
                self.coords.append([self.coords[-1][0]+1,self.coords[-1][1]])
                check=await self.apple_update()
        elif self.goto=="L":
            if self.coords[-1][0]-1<0 or [self.coords[-1][0]-1,self.coords[-1][1]] in self.coords:
                self.gameover=1
            else:
                self.coords.append([self.coords[-1][0]-1,self.coords[-1][1]])
                check=await self.apple_update()
        elif self.goto=="U":
            if self.coords[-1][1]-1<0 or [self.coords[-1][0],self.coords[-1][1]-1] in self.coords:
                self.gameover=1
            else:
                self.coords.append([self.coords[-1][0],self.coords[-1][1]-1])
                check=await self.apple_update()
        elif self.goto=="D":
            if self.coords[-1][1]+1>=12 or [self.coords[-1][0],self.coords[-1][1]+1] in self.coords:
                self.gameover=1
            else:
                self.coords.append([self.coords[-1][0],self.coords[-1][1]+1])
                check=await self.apple_update()
        pass
        if not check and not self.gameover:
            self.coords.pop(0)
        else:
            self.score+=10
    async def retext(self):
        await self.snake_update()
        self.matrix=[["◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️","◼️"] for i in range(12)]
        for coord in self.coords:
            self.matrix[coord[1]][coord[0]]="🟩"
        self.matrix[self.apple[1]][self.apple[0]]="🟥"
    async def redraw(self):
        await self.snake_update()
        self.image=Image.new('RGB',(240,240),'black')
        idraw=ImageDraw.Draw(self.image)
        for coord in self.coords:
            idraw.rectangle((coord[0]*20,coord[1]*20,(coord[0]+1)*20,(coord[1]+1)*20),fill="green")
        idraw.rectangle((self.apple[0]*20,self.apple[1]*20,(self.apple[0]+1)*20,(self.apple[1]+1)*20),fill="red")
        pass
    async def get_image(self):
        await asyncio.sleep(0.4)
        await self.redraw()
        with io.BytesIO() as image_binary:
            self.image.save(image_binary,"PNG")
            image_binary.seek(0)
            self.file=discord.File(fp=image_binary, filename='image.png')
            self.embed.set_image(url=("attachment://"+self.file.filename))
        return self.file, self.embed
    async def get_text(self):
        await asyncio.sleep(0.4)
        await self.retext()
        s=""
        for elements in self.matrix:
            for element in elements:
                s+=element
            s+='\n'
        self.embed.description="**"+s+"**"
        if self.gameover:
            self.embed.title="Score: "+str(self.score-10)
        return self.embed,self.gameover
    @discord.ui.button(style = ButtonStyle.grey,emoji = '🔴',custom_id = "00",row=0)
    async def button_callback00(self,interaction: discord.Interaction,button:Button):
        await interaction.response.defer()
    @discord.ui.button(style = ButtonStyle.grey,emoji = '⬆️',custom_id = "01",row=0)
    async def button_callback01(self,interaction: discord.Interaction,button:Button):
        if self.goto!="D":
            self.goto="U"
        await interaction.response.defer()
    @discord.ui.button(style = ButtonStyle.grey,emoji = '🔴',custom_id = "02",row=0)
    async def button_callback02(self,interaction: discord.Interaction,button:Button):
        await interaction.response.defer()
    @discord.ui.button(style = ButtonStyle.grey,emoji = '⬅️',custom_id = "10",row=1)
    async def button_callback10(self,interaction: discord.Interaction,button:Button):
        if self.goto!="R":
            self.goto="L"
        await interaction.response.defer()
    @discord.ui.button(style = ButtonStyle.grey,emoji = '⬇️',custom_id = "11",row=1)
    async def button_callback11(self,interaction: discord.Interaction,button:Button):
        if self.goto!="U":
            self.goto="D"
        await interaction.response.defer()
    @discord.ui.button(style = ButtonStyle.grey,emoji = '➡️',custom_id = "12",row=1)
    async def button_callback12(self,interaction: discord.Interaction,button:Button):
        if self.goto!="L":
            self.goto="R"
        await interaction.response.defer()