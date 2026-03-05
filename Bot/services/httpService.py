try:
    import aiohttp
except Exception:  # pragma: no cover - optional import guard for local environments
    aiohttp = None


class HttpService:
    def __init__(
        self,
        timeout_seconds: int = 10,
        *,
        proxy_url: str | None = None,
        proxy_username: str | None = None,
        proxy_password: str | None = None,
    ):
        self.timeout_seconds = timeout_seconds
        self.proxy_url = str(proxy_url or "").strip() or None
        self.proxy_username = str(proxy_username or "").strip() or None
        self.proxy_password = str(proxy_password or "")

    def _proxy_kwargs(self) -> dict:
        if not self.proxy_url:
            return {}
        kwargs = {"proxy": self.proxy_url}
        if self.proxy_username:
            if aiohttp is None:
                raise RuntimeError("aiohttp is not installed")
            kwargs["proxy_auth"] = aiohttp.BasicAuth(self.proxy_username, self.proxy_password)
        return kwargs

    async def get_json(self, url: str, headers: dict | None = None):
        if aiohttp is None:
            raise RuntimeError("aiohttp is not installed")
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, **self._proxy_kwargs()) as response:
                response.raise_for_status()
                return await response.json(content_type=None)

    async def get_text(self, url: str, headers: dict | None = None) -> str:
        if aiohttp is None:
            raise RuntimeError("aiohttp is not installed")
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers, **self._proxy_kwargs()) as response:
                response.raise_for_status()
                return await response.text()

    async def post_form_json(self, url: str, data: dict, headers: dict | None = None):
        if aiohttp is None:
            raise RuntimeError("aiohttp is not installed")
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        request_headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if headers:
            request_headers.update(headers)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                url,
                data=data,
                headers=request_headers,
                **self._proxy_kwargs(),
            ) as response:
                response.raise_for_status()
                return await response.json(content_type=None)
