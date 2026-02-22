from pathlib import Path

import discord
from discord.ext import commands

from Config.config import settings_bot


BASE_DIR = Path(__file__).resolve().parent
COMMANDS_DIR = BASE_DIR / "Commands"
EVENTS_DIR = BASE_DIR / "Events"


def create_bot() -> commands.Bot:
    intents = discord.Intents.all()
    return commands.Bot(
        command_prefix=settings_bot["prefix"],
        intents=intents,
        help_command=None,
    )


def _iter_extensions(folder: Path, module_prefix: str):
    for file_path in sorted(folder.glob("*.py")):
        if file_path.stem.startswith("_"):
            continue
        yield f"{module_prefix}.{file_path.stem}"


async def load_extensions(bot_instance: commands.Bot):
    for extension in _iter_extensions(COMMANDS_DIR, "Commands"):
        await bot_instance.load_extension(extension)
    for extension in _iter_extensions(EVENTS_DIR, "Events"):
        await bot_instance.load_extension(extension)


def configure_setup_hook(bot_instance: commands.Bot):
    async def _setup_hook():
        await load_extensions(bot_instance)

    bot_instance.setup_hook = _setup_hook


bot = create_bot()
configure_setup_hook(bot)


if __name__ == "__main__":
    if not settings_bot["token"] or settings_bot["token"] == "mock_api_key":
        raise RuntimeError(
            "DISCORD_TOKEN (or BOT_TOKEN/TOKEN) is not configured in environment."
        )
    bot.run(settings_bot["token"])
