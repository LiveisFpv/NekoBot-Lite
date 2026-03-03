from collections.abc import Awaitable, Callable

import discord
from discord import ButtonStyle
from discord.ui import Button, View

ActionHandler = Callable[[str, discord.Interaction, View], Awaitable[None] | None]


class PlayerView(View):
    def __init__(
        self,
        *,
        on_action: ActionHandler | None = None,
        loop_enabled: bool = False,
        loop_one_enabled: bool = False,
        timeout: float | None = 36000,
    ):
        super().__init__(timeout=timeout)
        self.on_action = on_action
        self.response = ""
        self.message_id = ""

        for child in self.children:
            if not isinstance(child, Button):
                continue
            if child.custom_id == "loop":
                child.style = ButtonStyle.green if loop_enabled else ButtonStyle.grey
            elif child.custom_id == "loop1":
                child.style = ButtonStyle.green if loop_one_enabled else ButtonStyle.grey

    async def _dispatch_action(self, action: str, interaction: discord.Interaction):
        self.response = action
        self.message_id = str(interaction.message.id) if interaction.message else ""

        if self.on_action is not None:
            result = self.on_action(action, interaction, self)
            if isinstance(result, Awaitable):
                await result

        if not interaction.response.is_done():
            await interaction.response.defer()

    @discord.ui.button(style=ButtonStyle.grey, emoji="⏮️", custom_id="back", row=0)
    async def button_callback_back(self, interaction: discord.Interaction, button: Button):
        await self._dispatch_action("back", interaction)

    @discord.ui.button(style=ButtonStyle.grey, emoji="⏯️", custom_id="pla", row=0)
    async def button_callback_play(self, interaction: discord.Interaction, button: Button):
        await self._dispatch_action("play", interaction)

    @discord.ui.button(style=ButtonStyle.grey, emoji="⏭️", custom_id="skip", row=0)
    async def button_callback_skip(self, interaction: discord.Interaction, button: Button):
        await self._dispatch_action("skip", interaction)

    @discord.ui.button(style=ButtonStyle.grey, emoji="🔀", custom_id="shuffle", row=0)
    async def button_callback_shuffle(self, interaction: discord.Interaction, button: Button):
        await self._dispatch_action("shuffle", interaction)

    @discord.ui.button(style=ButtonStyle.grey, emoji="🔁", custom_id="loop", row=1)
    async def button_callback_loop(self, interaction: discord.Interaction, button: Button):
        await self._dispatch_action("loop", interaction)

    @discord.ui.button(style=ButtonStyle.grey, emoji="🔂", custom_id="loop1", row=1)
    async def button_callback_loop1(self, interaction: discord.Interaction, button: Button):
        await self._dispatch_action("loop1", interaction)

    @discord.ui.button(style=ButtonStyle.grey, emoji="🛑", custom_id="stop", row=1)
    async def button_callback_stop(self, interaction: discord.Interaction, button: Button):
        await self._dispatch_action("stop", interaction)


# Backward-compatible alias used by existing imports.
playerView = PlayerView
