import aiohttp


class HttpService:
    def __init__(self, timeout_seconds: int = 10):
        self.timeout_seconds = timeout_seconds

    async def get_json(self, url: str, headers: dict | None = None):
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                return await response.json(content_type=None)

    async def get_text(self, url: str, headers: dict | None = None) -> str:
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                return await response.text()
