import pytest
from unittest.mock import AsyncMock
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Импортируем код бота
from main import bot,load_extensions
@pytest.mark.asyncio
async def test_ping_command():
    # Загрузить команды перед выполнением теста
    await load_extensions()

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