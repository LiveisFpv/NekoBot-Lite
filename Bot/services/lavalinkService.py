import asyncio
import os

from utils.utils import log

try:
    import wavelink
except Exception:  # pragma: no cover - optional import guard for local environments
    wavelink = None


class LavalinkService:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        password: str,
        secure: bool,
        retries: int = 5,
        retry_backoff: float = 1.5,
    ):
        self.host = host
        self.port = port
        self.password = password
        self.secure = secure
        self.retries = retries
        self.retry_backoff = retry_backoff

    @classmethod
    def from_env(cls):
        host = os.getenv("LAVALINK_HOST", "lavalink")
        port = int(os.getenv("LAVALINK_PORT", "2333"))
        password = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")
        secure_raw = os.getenv("LAVALINK_SECURE", "false").strip().lower()
        secure = secure_raw in {"1", "true", "yes", "on"}
        retries = int(os.getenv("LAVALINK_RETRIES", "5"))
        retry_backoff = float(os.getenv("LAVALINK_RETRY_BACKOFF", "1.5"))

        return cls(
            host=host,
            port=port,
            password=password,
            secure=secure,
            retries=max(1, retries),
            retry_backoff=max(0.1, retry_backoff),
        )

    @property
    def uri(self) -> str:
        scheme = "https" if self.secure else "http"
        return f"{scheme}://{self.host}:{self.port}"

    @staticmethod
    def is_wavelink_available() -> bool:
        return wavelink is not None

    @staticmethod
    def has_nodes() -> bool:
        return bool(wavelink and wavelink.Pool.nodes)

    async def connect(self, bot) -> bool:
        if wavelink is None:
            await log("ERROR: Wavelink is not installed. Lavalink playback is unavailable.")
            return False

        if self.has_nodes():
            return True

        delay = self.retry_backoff
        for attempt in range(1, self.retries + 1):
            try:
                node = wavelink.Node(
                    identifier="main",
                    uri=self.uri,
                    password=self.password,
                    retries=1,
                    client=bot,
                )
                await wavelink.Pool.connect(nodes=[node], client=bot, cache_capacity=100)
                await log(f"INFO: Connected to Lavalink node at {self.uri}")
                return True
            except Exception as exc:
                await log(
                    f"WARNING: Lavalink connect attempt {attempt}/{self.retries} failed: {exc}"
                )
                if attempt < self.retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 10.0)

        await log("ERROR: Could not connect to Lavalink after retries.")
        return False

    async def ensure_connected(self, bot) -> bool:
        if self.has_nodes():
            return True
        return await self.connect(bot)
