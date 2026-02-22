import asyncio
from pathlib import Path

from googletrans import Translator

from services.httpService import HttpService


class GeneralService:
    SUPPORT_IMAGE_ENDPOINT = "https://api.waifu.pics/sfw/hug"
    MD_DIR = Path(__file__).resolve().parents[1] / "md"

    def __init__(self, http_service: HttpService | None = None):
        self.http_service = http_service or HttpService()
        self._md_cache: dict[str, str] = {}

    def _read_md(self, filename: str) -> str:
        if filename not in self._md_cache:
            file_path = self.MD_DIR / filename
            self._md_cache[filename] = file_path.read_text(encoding="utf-8")
        return self._md_cache[filename]

    def get_version_text(self) -> str:
        return self._read_md("update.md")

    def get_help_text(self) -> str:
        return self._read_md("help.md")

    def get_music_help_text(self) -> str:
        return self._read_md("play_help.md")

    async def get_support_image_url(self) -> str | None:
        data = await self.http_service.get_json(self.SUPPORT_IMAGE_ENDPOINT)
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
        result = translator.translate(text=text, dest="ru")
        return result.text
