from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from services.httpService import HttpService


class SpotifyIntegrationError(Exception):
    pass


class SpotifyConfigError(SpotifyIntegrationError):
    pass


class SpotifyApiError(SpotifyIntegrationError):
    pass


@dataclass(frozen=True)
class SpotifyEntityRef:
    kind: str
    entity_id: str


class SpotifyService:
    TOKEN_URL = "https://accounts.spotify.com/api/token"
    API_BASE = "https://api.spotify.com/v1"
    MAX_PAGE_LIMIT = 50

    def __init__(
        self,
        *,
        http_service: HttpService | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        self.http_service = http_service or HttpService()
        self.client_id = (client_id or os.getenv("SPOTIFY_CLIENT_ID", "")).strip()
        self.client_secret = (client_secret or os.getenv("SPOTIFY_CLIENT_SECRET", "")).strip()
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    @staticmethod
    def is_spotify_url(value: str) -> bool:
        parsed = urlparse((value or "").strip())
        if parsed.scheme not in {"http", "https"}:
            return False
        host = (parsed.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host == "spotify.com" or host.endswith(".spotify.com")

    @staticmethod
    def parse_spotify_url(value: str) -> SpotifyEntityRef:
        parsed = urlparse((value or "").strip())
        host = (parsed.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        if not (host == "spotify.com" or host.endswith(".spotify.com")):
            raise SpotifyApiError("Unsupported Spotify host.")

        segments = [segment for segment in parsed.path.split("/") if segment]
        valid_kinds = {"track", "playlist", "album"}

        for idx, segment in enumerate(segments):
            segment_l = segment.strip().lower()
            if segment_l in valid_kinds and idx + 1 < len(segments):
                entity_id = segments[idx + 1].strip()
                if entity_id:
                    return SpotifyEntityRef(kind=segment_l, entity_id=entity_id)

        raise SpotifyApiError("Unsupported Spotify URL path.")

    @staticmethod
    def build_search_query(name: str, artists: list[str]) -> str:
        clean_name = str(name or "").strip()
        artist_values = [str(item or "").strip() for item in artists if str(item or "").strip()]
        if artist_values and clean_name:
            return f"{', '.join(artist_values)} - {clean_name}"
        return clean_name

    def _ensure_credentials(self) -> None:
        if not self.client_id or not self.client_secret:
            raise SpotifyConfigError(
                "Spotify credentials are not configured. "
                "Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET."
            )

    async def _get_access_token(self) -> str:
        now = time.time()
        if self._access_token and now < (self._token_expires_at - 30):
            return self._access_token

        self._ensure_credentials()
        raw_auth = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        basic = base64.b64encode(raw_auth).decode("ascii")

        try:
            payload = await self.http_service.post_form_json(
                self.TOKEN_URL,
                data={"grant_type": "client_credentials"},
                headers={"Authorization": f"Basic {basic}"},
            )
        except Exception as exc:
            raise SpotifyApiError("Failed to fetch Spotify access token.") from exc

        token = str(payload.get("access_token") or "").strip()
        expires_in = int(payload.get("expires_in") or 3600)
        if not token:
            raise SpotifyApiError("Spotify returned empty access token.")

        self._access_token = token
        self._token_expires_at = now + max(60, expires_in)
        return token

    async def _auth_headers(self) -> dict[str, str]:
        token = await self._get_access_token()
        return {"Authorization": f"Bearer {token}"}

    async def _get_json(self, url: str) -> dict:
        headers = await self._auth_headers()
        try:
            payload = await self.http_service.get_json(url, headers=headers)
        except Exception as exc:
            raise SpotifyApiError(f"Spotify API request failed: {url}") from exc
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _track_to_query(track_payload: dict | None) -> str:
        if not isinstance(track_payload, dict):
            return ""
        name = str(track_payload.get("name") or "").strip()
        artists_raw = track_payload.get("artists") or []
        artists: list[str] = []
        if isinstance(artists_raw, list):
            for item in artists_raw:
                if isinstance(item, dict):
                    value = str(item.get("name") or "").strip()
                    if value:
                        artists.append(value)
        return SpotifyService.build_search_query(name, artists)

    async def _get_playlist_name(self, playlist_id: str) -> str:
        payload = await self._get_json(f"{self.API_BASE}/playlists/{playlist_id}")
        return str(payload.get("name") or "").strip() or playlist_id

    async def _get_album_name(self, album_id: str) -> str:
        payload = await self._get_json(f"{self.API_BASE}/albums/{album_id}")
        return str(payload.get("name") or "").strip() or album_id

    @staticmethod
    def _parse_next_offset(next_url: str | None) -> int | None:
        if not next_url:
            return None
        parsed = urlparse(next_url)
        query = parse_qs(parsed.query)
        offset_values = query.get("offset")
        if not offset_values:
            return None
        try:
            return int(offset_values[0])
        except Exception:
            return None

    async def fetch_deferred_queries(
        self,
        cursor: dict,
        *,
        batch_size: int = 50,
    ) -> tuple[list[str], dict | None]:
        if not isinstance(cursor, dict):
            return [], None

        kind = str(cursor.get("kind") or "").strip().lower()
        entity_id = str(cursor.get("entity_id") or "").strip()
        display_title = str(cursor.get("display_title") or "").strip()
        offset = int(cursor.get("offset") or 0)
        page_limit = max(1, min(int(batch_size), self.MAX_PAGE_LIMIT))

        if kind not in {"playlist", "album"} or not entity_id:
            return [], None

        if kind == "playlist":
            url = (
                f"{self.API_BASE}/playlists/{entity_id}/tracks"
                f"?offset={offset}&limit={page_limit}&additional_types=track"
            )
            payload = await self._get_json(url)
            items = payload.get("items") or []
            queries: list[str] = []
            for item in items if isinstance(items, list) else []:
                track_payload = item.get("track") if isinstance(item, dict) else None
                if isinstance(track_payload, dict) and track_payload.get("is_local"):
                    continue
                query = self._track_to_query(track_payload)
                if query:
                    queries.append(query)
        else:
            url = f"{self.API_BASE}/albums/{entity_id}/tracks?offset={offset}&limit={page_limit}"
            payload = await self._get_json(url)
            items = payload.get("items") or []
            queries = []
            for item in items if isinstance(items, list) else []:
                query = self._track_to_query(item if isinstance(item, dict) else None)
                if query:
                    queries.append(query)

        next_offset = self._parse_next_offset(payload.get("next"))
        if next_offset is None:
            return queries, None

        next_cursor = {
            "kind": kind,
            "entity_id": entity_id,
            "display_title": display_title or entity_id,
            "offset": next_offset,
        }
        return queries, next_cursor

    async def resolve_for_enqueue(self, query: str, *, initial_limit: int = 100) -> dict:
        reference = self.parse_spotify_url(query)
        if reference.kind == "track":
            payload = await self._get_json(f"{self.API_BASE}/tracks/{reference.entity_id}")
            search_query = self._track_to_query(payload)
            return {
                "kind": "track",
                "display_title": str(payload.get("name") or "").strip() or reference.entity_id,
                "initial_queries": [search_query] if search_query else [],
                "deferred_cursor": None,
            }

        if reference.kind == "playlist":
            display_title = await self._get_playlist_name(reference.entity_id)
        else:
            display_title = await self._get_album_name(reference.entity_id)

        limit = max(1, int(initial_limit))
        cursor: dict | None = {
            "kind": reference.kind,
            "entity_id": reference.entity_id,
            "display_title": display_title,
            "offset": 0,
        }
        initial_queries: list[str] = []

        while cursor is not None and len(initial_queries) < limit:
            remaining = limit - len(initial_queries)
            batch_queries, cursor = await self.fetch_deferred_queries(
                cursor,
                batch_size=min(self.MAX_PAGE_LIMIT, remaining),
            )
            if batch_queries:
                initial_queries.extend(batch_queries)
            elif cursor is None:
                break

        return {
            "kind": reference.kind,
            "display_title": display_title,
            "initial_queries": initial_queries[:limit],
            "deferred_cursor": cursor,
        }
