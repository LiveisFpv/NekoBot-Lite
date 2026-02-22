import json
import random
from urllib.parse import quote_plus

from services.httpService import HttpService


class AnimeService:
    API_URL = "https://www.animecharactersdatabase.com/api_series_characters.php?character_q="
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/96.0.4664.45 Safari/537.36"
        )
    }

    def __init__(self, http_service: HttpService | None = None):
        self.http_service = http_service or HttpService(timeout_seconds=15)

    async def find_character(self, query: str):
        normalized_query = (query or "naruto").strip().lower()
        url = f"{self.API_URL}{quote_plus(normalized_query)}"
        body = await self.http_service.get_text(url, headers=self.HEADERS)

        if body.strip() == "-1":
            return None

        payload = json.loads(body)
        search_results = payload.get("search_results", [])
        if not search_results:
            return None

        matching_results = [
            item
            for item in search_results
            if normalized_query in item.get("name", "").lower().split()
        ]

        source = matching_results or search_results
        return random.choice(source)
