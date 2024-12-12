# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12.4
FROM python:${PYTHON_VERSION}-slim as base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY . /app
WORKDIR /app/server_conf

# Создаем пользователя с домашним каталогом
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/home/appuser" \
    --shell "/bin/bash" \
    --uid "${UID}" \
    appuser \
    && mkdir -p /home/appuser/.cache/yt-dlp \
    && chown -R appuser:appuser /home/appuser

# Устанавливаем зависимости
RUN apt-get update && apt-get install -y \
    libkrb5-dev \
    build-essential \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Python-зависимости
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=server_conf/requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

# Настраиваем окружение для yt-dlp
ENV HOME=/home/appuser
ENV YTDLP_CACHE_DIR=/home/appuser/.cache/yt-dlp

# Переключаемся на пользователя
USER appuser

# Порт, используемый приложением
EXPOSE 4545

WORKDIR /app

# Запускаем приложение
CMD ["python", "./Bot/main.py"]
