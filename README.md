# NekoBot Lite

Discord bot on Python with commands for memes, Reddit, anime search, and music playback in voice channels.

## Current Status

- Service-based architecture is used in command groups.
- Music playback migrated to Lavalink/Wavelink for low-gap track transitions.

## Tech Stack

- Python 3.12
- `discord.py`
- `wavelink` + Lavalink v4 for music playback
- `aiohttp` for async HTTP requests
- `asyncpraw` for Reddit API

## Architecture

- Entry point and bootstrap:
  - `Bot/main.py`
- Discord adapter layer (commands/events):
  - `Bot/Commands/*.py`
  - `Bot/Events/*.py`
- Service layer:
  - `Bot/services/httpService.py`
  - `Bot/services/generalService.py`
  - `Bot/services/animeService.py`
  - `Bot/services/memeService.py`
  - `Bot/services/redditService.py`
  - `Bot/services/lavalinkService.py`
  - `Bot/services/mediaService.py`
  - `Bot/services/mediaPlaybackService.py`
- UI components for Discord interactions:
  - `Bot/Music_player/music_player.py`
- Tests:
  - `Bot/tests/test_bot.py`
  - `Bot/tests/test_services.py`

## Development Status

- Core command groups are migrated to services.
- Media playback uses Lavalink queue/events instead of `yt-dlp` polling loops.
- `%play` and `/play` are both supported in a shared implementation.
- Extension loading and startup flow are centralized in `Bot/main.py`.

## Roadmap

- Additional command catalog improvements in Discord UI and bot profile.

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

- `%play <url or search query>`
- `%pause`
- `%resume`
- `%skip`
- `%leave`

Notes:

- `%play` supports direct URLs from YouTube/SoundCloud, Spotify (`track`, `playlist`, `album`, `artist`) and Yandex Music (`track`, `playlist`, `album`).
- Spotify `track` is resolved by Lavalink + LavaSrc.
- Spotify `playlist` / `album` / `artist` use hybrid mode: Lavalink first, then bot web fallback if Lavalink cannot resolve.
- For Spotify anonymous token support, `spotify-tokener` is started in docker compose and used by LavaSrc.
- Yandex Music URLs are resolved through Lavalink + LavaSrc for metadata, then played via YouTube Music matches to avoid direct Yandex ad playback.
- `YANDEX_TOKEN` is still required for Yandex Music URLs because the bot still needs Yandex metadata resolution.

Game:

- `%snake`

## Environment Variables

Core:

- `DISCORD_TOKEN` (or `BOT_TOKEN` / `TOKEN`)
- `BOT_PREFIX` (default: `%`)
- `DISCORD_BOT_NAME`
- `DISCORD_BOT_ID`

Reddit:

- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`

Spotify:

- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_PROXY_URL` (optional, proxy for bot-side Spotify web fallback)
- `SPOTIFY_PROXY_USERNAME` (optional)
- `SPOTIFY_PROXY_PASSWORD` (optional)
- `SPOTIFY_PREFER_ANONYMOUS_TOKEN` (optional, default: `false`; set `true` only if needed for generated playlists)
- `SPOTIFY_TOKEN_ENDPOINT` (optional, LavaSrc anonymous token endpoint, default: `http://spotify-tokener:8080/api/token`)
- `SPOTIFY_MARKET` (optional, 2-letter market like `US` for LavaSrc Spotify resolver)

Yandex Music:

- `YANDEX_TOKEN`
- `YANDEX_PROXY_URL` (optional, proxy for Yandex metadata resolution only)
- `YANDEX_PROXY_USERNAME` (optional)
- `YANDEX_PROXY_PASSWORD` (optional)

Lavalink/Wavelink:

- `LAVALINK_HOST` (default: `lavalink`)
- `LAVALINK_PORT` (default: `2333`)
- `LAVALINK_PASSWORD` (default: `youshallnotpass`)
- `LAVALINK_SECURE` (default: `false`)
- `PLAYER_DEFAULT_VOLUME` (default: `100`)

## Docker Run

Start bot + Lavalink:

```bash
docker compose up -d --build
```

Pass required env vars through shell or `.env` file (`DISCORD_TOKEN` is mandatory).
You can start from `.env.example`.

## Tests

Run all tests:

```bash
pytest Bot/tests
```

## CI/CD

GitHub Actions workflow (`.github/workflows/python-ci.yml`) currently:

- runs tests on push to `main`
- deploys to VPS after successful test job
