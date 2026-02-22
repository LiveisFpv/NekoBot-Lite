import asyncio

from googletrans import Translator

from services.httpService import HttpService


class MemeService:
    ANIME_QUOTE_ENDPOINT = "https://some-random-api.ml/animu/quote"
    PIKACHU_ENDPOINT = "https://some-random-api.ml/img/pikachu"
    WAIFU_ENDPOINT = "https://api.waifu.pics/sfw/"

    def __init__(self, http_service: HttpService | None = None):
        self.http_service = http_service or HttpService()

    async def get_anime_quote(self):
        data = await self.http_service.get_json(self.ANIME_QUOTE_ENDPOINT)
        if isinstance(data, dict):
            return data
        return {}

    async def get_pikachu_image_url(self) -> str | None:
        data = await self.http_service.get_json(self.PIKACHU_ENDPOINT)
        if isinstance(data, dict):
            return data.get("link")
        return None

    async def get_waifu_image_url(self, category: str) -> str | None:
        target = (category or "waifu").strip()
        data = await self.http_service.get_json(f"{self.WAIFU_ENDPOINT}{target}")
        if isinstance(data, dict):
            return data.get("url")
        return None

    async def translate_to_ru(self, text: str) -> str:
        clean_text = text.strip()
        if not clean_text:
            return ""
        return await asyncio.to_thread(self._translate_to_ru_sync, clean_text)

    @staticmethod
    def _translate_to_ru_sync(text: str) -> str:
        translator = Translator()
        result = translator.translate(text=text, src="en", dest="ru")
        return result.text
