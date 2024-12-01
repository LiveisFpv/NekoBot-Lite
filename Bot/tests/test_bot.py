import pdb
import discord
import discord.ext.commands
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Импортируем код бота
import discord.ext
from main import bot,load_extensions
@pytest.mark.asyncio
async def test_load_extension():
    # Загрузить команды перед выполнением теста
    await load_extensions()
    
    # Проверяем, что все расширения загружены
    assert len(bot.extensions) == 7, "Не все расширения загружены"

@pytest.mark.asyncio
async def test_ping_command():
    # Загрузить команды перед выполнением теста
    # await load_extensions()

    # Создаем mock объект для ctx
    mock_ctx = AsyncMock()

    # Получаем команду 'ping'
    ping_command = bot.get_command('ping')
    # Проверяем, что команда найдена
    assert ping_command is not None, "Команда 'ping' не найдена"

    # Вызываем команду асинхронно
    await ping_command(mock_ctx)

    # Проверяем, что метод send был вызван
    mock_ctx.send.assert_called_once()

@pytest.mark.asyncio
async def test_version_command():
    # Загрузить команды перед выполнением теста
    # await load_extensions()
    # Создаем mock объект для ctx
    mock_ctx = AsyncMock()
    
    # Получаем команду 'version'
    version_command = bot.get_command('version')
    # Проверяем, что команда найдена
    assert version_command is not None, "Команда 'version' не найдена"
    
    # Вызываем команду асинхронно
    await version_command(mock_ctx)
    # Проверяем, что метод send был вызван с версией бота
    mock_ctx.send.assert_called_once()

@pytest.mark.asyncio
async def test_help_command():
    # Создаем mock объект для ctx
    mock_ctx = AsyncMock()

    # Создаем mock для avatar и user
    mock_avatar = MagicMock()
    mock_avatar.url = "https://example.com/avatar.png"
    mock_bot_user = MagicMock()
    mock_bot_user.avatar = mock_avatar

    # Создаем mock объект для bot и присваиваем mock_user
    mock_bot = MagicMock(spec=discord.ext.commands.Bot)
    mock_bot.user = mock_bot_user

    # Создаем mock для команды help
    help_command = AsyncMock()
    mock_bot.get_command.return_value = help_command

    # Используем patch, чтобы замокать self.bot
    with patch('main.bot', mock_bot):
        # Получаем команду 'help'
        help_command = mock_bot.get_command('help')

        # Проверяем, что команда найдена
        assert help_command is not None, "Команда 'help' не найдена"
        pdb.set_trace()
        # Вызываем команду асинхронно
        result = await help_command(mock_ctx)
        # Проверяем, что команда была вызвана
        help_command.assert_awaited_once_with(mock_ctx)

@pytest.mark.asyncio
async def test_support():
    # Загрузить команды перед выполнением теста
    # await load_extensions()
    # Создаем mock объект для ctx
    mock_ctx = AsyncMock()
    
    # Получаем команду 'support'
    support_command = bot.get_command('support')
    # Проверяем, что команда найдена
    assert support_command is not None, "Команда 'support' не найдена"
    
    # Вызываем команду асинхронно
    await support_command(mock_ctx)
    # Проверяем, что метод send был вызван с ссылкой на поддержку
    mock_ctx.send.assert_called_once()
