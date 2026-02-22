import io
from discord.ui import Button, View
import discord
from discord import ButtonStyle


class playerView(View):
    response=''
    message_id=''
    LOOP=ButtonStyle.grey
    LOOPSTYLE=ButtonStyle.grey
    
    @discord.ui.button(style = ButtonStyle.grey,emoji = '⏮',custom_id = "back",row=0)
    async def button_callback1(self,interaction: discord.Interaction,button:Button):
        self.response="back"
        self.message_id=interaction.message.id
        await interaction.response.defer()
        
    @discord.ui.button(style = ButtonStyle.grey,emoji = '⏯',custom_id = "pla",row=0)
    async def button_callback2(self,interaction: discord.Interaction,button:Button):
        self.response="play"
        self.message_id=interaction.message.id
        await interaction.response.defer()
        
    @discord.ui.button(style = ButtonStyle.grey,emoji = '⏭',custom_id = "skip",row=0)
    async def button_callback3(self,interaction: discord.Interaction,button:Button):
        self.response="skip"
        self.message_id=interaction.message.id
        await interaction.response.defer()
        
    @discord.ui.button(style = ButtonStyle.grey,emoji = '🔁',custom_id = "loop",row=1)
    async def button_callback4(self,interaction: discord.Interaction,button:Button):
        self.response="loop"
        self.message_id=interaction.message.id
        if button.style==ButtonStyle.green:
            button.style=ButtonStyle.grey
        else:
            button.style=ButtonStyle.green
        await interaction.response.defer()
        
    @discord.ui.button(style = ButtonStyle.grey,emoji = '🔂',custom_id = "loop1",row=1)
    async def button_callback5(self,interaction: discord.Interaction,button:Button):
        self.response="loop1"
        self.message_id=interaction.message.id
        if button.style==ButtonStyle.green:
            button.style=ButtonStyle.grey
        else:
            button.style=ButtonStyle.green
        await interaction.response.defer()
        
    @discord.ui.button(style = ButtonStyle.grey,emoji = '⏹',custom_id = "stop",row=1)
    async def button_callback6(self,interaction: discord.Interaction,button:Button):
        self.response="stop"
        self.message_id=interaction.message.id
        await interaction.response.defer()
