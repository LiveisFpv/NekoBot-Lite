# NekoBot Lite

Discord bot on Python with commands for memes, Reddit, anime search, and music playback in voice channels.

## Current Status

- Refactor to service-based architecture is in progress and already used in core command groups.
- Latest in-project update note: (see `Bot/md/update.md`).

## Tech Stack

- Python 3.12
- `discord.py`
- `yt-dlp` + `ffmpeg` for music playback
- `aiohttp` for async HTTP requests
- `asyncpraw` for Reddit API

## Architecture

The project is organized as a monolith:

- Entry point and bootstrap:
  - `Bot/main.py`
- Discord adapter layer (commands/events):
  - `Bot/Commands/*.py`
  - `Bot/Events/*.py`
- Service layer (business logic):
  - `Bot/services/httpService.py`
  - `Bot/services/generalService.py`
  - `Bot/services/animeService.py`
  - `Bot/services/memeService.py`
  - `Bot/services/redditService.py`
  - `Bot/services/mediaService.py`
  - `Bot/services/mediaPlaybackService.py`
- UI components for Discord interactions:
  - `Bot/Music_player/music_player.py`
- Tests:
  - `Bot/tests/test_bot.py`
  - `Bot/tests/test_services.py`

## Development Status

- Core command groups are migrated to services.
- Media playback is split into queue/state and playback orchestration services.
- Extension loading and startup flow are centralized in `Bot/main.py`.
- Test suite is green in CI (`pytest Bot/tests`).

## Roadmap

- Spotify integration for music commands (search/import/play flow).
- Migration from prefix-only commands to Discord application commands (slash commands).
- Bot command catalog improvements so commands are visible in Discord command UI and bot profile.

## Available Commands (Default prefix: `%`)

General:

- `%help`
- `%version`
- `%ping`
- `%support`
- `%trans <text>`

Anime:

- `%c <character name>`
- `%anime`

Meme/Media:

- `%meme`
- `%animeme`
- `%genshin`
- `%potato`
- `%pikachu`
- `%waifu`
- `%waifu help`
- `%FBI`

Reddit:

- `%Reddit <subreddit name>`

Music:

- `%play <url>`
- `%pause`
- `%resume`
- `%skip`
- `%leave`

Game:

- `%snake`

## Environment Variables

- `DISCORD_TOKEN` (or `BOT_TOKEN` / `TOKEN`)
- `BOT_PREFIX` (default: `%`)
- `DISCORD_BOT_NAME`
- `DISCORD_BOT_ID`
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`
- `YTDLP_REMOTE_COMPONENTS` (default: `ejs:github`)
- `YTDLP_CACHE_DIR`

## Docker Run

`docker-compose.yml` is ready for running the bot container:

```bash
docker compose up -d --build
```

Pass required env vars through shell or `.env` file (`DISCORD_TOKEN` is mandatory).

## Tests

Run all tests:

```bash
pytest Bot/tests
```

## CI/CD

GitHub Actions workflow (`.github/workflows/python-ci.yml`) currently:

- runs tests on push to `main`
- deploys to VPS after successful test job
