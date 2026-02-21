import os


def _get_env(name: str, default=None):
    v = os.getenv(name)
    if v is not None and str(v).strip() != "":
        return v
    return default


def _get_int(name: str, default: int = 0) -> int:
    v = _get_env(name)
    try:
        return int(v) if v is not None else default
    except Exception:
        return default


settings_bot = {
    "token": _get_env("DISCORD_TOKEN")
    or _get_env("BOT_TOKEN")
    or _get_env("TOKEN")
    or "mock_api_key",
    "bot": _get_env("BOT_NAME") or _get_env("DISCORD_BOT_NAME") or "NEKO",
    "id": _get_int("BOT_ID", _get_int("DISCORD_BOT_ID", 0)),
    "prefix": _get_env("BOT_PREFIX", "%"),
}

reddit_api = {
    "client_id": _get_env("REDDIT_CLIENT_ID", "mock_api_key"),
    "client_secret": _get_env("REDDIT_CLIENT_SECRET", "mock_api_key"),
    "user_agent": _get_env("REDDIT_USER_AGENT", "mock_api_key"),
}
