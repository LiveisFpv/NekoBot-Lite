# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12.4
FROM python:${PYTHON_VERSION}-slim as base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY . /app
WORKDIR /app/server_conf

ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/home/appuser" \
    --shell "/bin/bash" \
    --uid "${UID}" \
    appuser

RUN apt-get update && apt-get install -y \
    libkrb5-dev \
    build-essential \
    ffmpeg \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=server_conf/requirements.txt,target=server_conf/requirements.txt \
    python -m pip install -r server_conf/requirements.txt

USER appuser

EXPOSE 4545

WORKDIR /app

CMD ["python", "Bot/main.py"]
