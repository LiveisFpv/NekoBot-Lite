from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, parse_qsl, urlencode, urlparse, urlunparse

from services.httpService import HttpRequestError, HttpService


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
        self.http_service = http_service or HttpService(
            proxy_url=self._get_env_str("SPOTIFY_PROXY_URL") or None,
            proxy_username=self._get_env_str("SPOTIFY_PROXY_USERNAME") or None,
            proxy_password=os.getenv("SPOTIFY_PROXY_PASSWORD", ""),
        )
        self.client_id = (client_id or os.getenv("SPOTIFY_CLIENT_ID", "")).strip()
        self.client_secret = (client_secret or os.getenv("SPOTIFY_CLIENT_SECRET", "")).strip()
        market = self._get_env_str("SPOTIFY_MARKET").upper()
        self.market = market if len(market) == 2 else ""
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    @staticmethod
    def _get_env_str(name: str) -> str:
        return str(os.getenv(name, "")).strip()

    @staticmethod
    def _safe_int(value: object) -> int | None:
        try:
            return int(value)  # type: ignore[arg-type]
        except Exception:
            return None

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
        valid_kinds = {"track", "playlist", "album", "artist"}

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
            details = f"{type(exc).__name__}: {exc}"
            if isinstance(exc, HttpRequestError):
                details = f"{type(exc).__name__}: status={exc.status}, body={exc.body[:300]}"
            raise SpotifyApiError(
                "Failed to fetch Spotify access token: "
                f"{details}"
            ) from exc

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

    def _with_market(self, url: str) -> str:
        if not self.market:
            return url
        parsed = urlparse(url)
        query_items = parse_qsl(parsed.query, keep_blank_values=True)
        query_keys = {key for key, _ in query_items}
        if "market" in query_keys or "from_token" in query_keys:
            return url
        query_items.append(("market", self.market))
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                urlencode(query_items),
                parsed.fragment,
            )
        )

    async def _get_json(self, url: str) -> dict:
        request_url = self._with_market(url)
        headers = await self._auth_headers()
        try:
            payload = await self.http_service.get_json(request_url, headers=headers)
        except Exception as exc:
            details = f"{type(exc).__name__}: {exc}"
            if isinstance(exc, HttpRequestError):
                details = f"{type(exc).__name__}: status={exc.status}, body={exc.body[:300]}"
                if exc.status == 403:
                    details += (
                        " | hint: playlist may be unavailable for current app flow/region; "
                        "try SPOTIFY_MARKET=US or OAuth user token for private/collab playlists"
                    )
            raise SpotifyApiError(
                f"Spotify API request failed: {request_url} ({details})"
            ) from exc
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

    @classmethod
    def _playlist_items_to_queries(
        cls,
        items_raw: object,
        *,
        limit: int | None = None,
    ) -> tuple[list[str], int]:
        if not isinstance(items_raw, list):
            return [], 0

        max_queries = None if limit is None else max(0, int(limit))
        if max_queries == 0:
            return [], 0

        queries: list[str] = []
        consumed_items = 0
        for item in items_raw:
            consumed_items += 1
            track_payload = item.get("track") if isinstance(item, dict) else None
            if isinstance(track_payload, dict) and track_payload.get("is_local"):
                if max_queries is not None and len(queries) >= max_queries:
                    break
                continue
            query = cls._track_to_query(track_payload if isinstance(track_payload, dict) else None)
            if query:
                queries.append(query)
            if max_queries is not None and len(queries) >= max_queries:
                break

        return queries, consumed_items

    async def _get_playlist_payload(self, playlist_id: str) -> dict[str, object]:
        payload = await self._get_json(f"{self.API_BASE}/playlists/{playlist_id}")
        tracks_payload = payload.get("tracks")
        tracks = tracks_payload if isinstance(tracks_payload, dict) else {}
        items_raw = tracks.get("items")
        items = items_raw if isinstance(items_raw, list) else []
        return {
            "display_title": str(payload.get("name") or "").strip() or playlist_id,
            "items": items,
            "offset": self._safe_int(tracks.get("offset")) or 0,
            "next_offset": self._parse_next_offset(str(tracks.get("next") or "")),
            "total": self._safe_int(tracks.get("total")),
        }

    async def _get_album_name(self, album_id: str) -> str:
        payload = await self._get_json(f"{self.API_BASE}/albums/{album_id}")
        return str(payload.get("name") or "").strip() or album_id

    async def _get_artist_name(self, artist_id: str) -> str:
        payload = await self._get_json(f"{self.API_BASE}/artists/{artist_id}")
        return str(payload.get("name") or "").strip() or artist_id

    async def _get_artist_top_track_queries(self, artist_id: str, *, limit: int) -> list[str]:
        market = self.market or "US"
        payload = await self._get_json(
            f"{self.API_BASE}/artists/{artist_id}/top-tracks?market={market}"
        )
        tracks = payload.get("tracks") or []
        queries: list[str] = []
        for item in tracks if isinstance(tracks, list) else []:
            query = self._track_to_query(item if isinstance(item, dict) else None)
            if query:
                queries.append(query)
            if len(queries) >= limit:
                break
        return queries

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

    @staticmethod
    def _playlist_has_more_items(
        *,
        consumed_items: int,
        bootstrap_items_count: int,
        current_offset: int,
        total_tracks: int | None,
        next_offset: int | None,
    ) -> bool:
        if consumed_items < bootstrap_items_count:
            return True
        if isinstance(total_tracks, int):
            return current_offset < total_tracks
        return next_offset is not None

    @staticmethod
    def _build_partial_reason(exc: Exception) -> str:
        cause = getattr(exc, "__cause__", None)
        if isinstance(cause, HttpRequestError):
            return f"Spotify API pagination failed with HTTP {cause.status}"
        return f"Spotify API pagination failed: {type(exc).__name__}"

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
        offset = self._safe_int(cursor.get("offset")) or 0
        page_limit = max(1, min(int(batch_size), self.MAX_PAGE_LIMIT))

        if kind not in {"playlist", "album"} or not entity_id:
            return [], None

        payload: dict
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
                query = self._track_to_query(track_payload if isinstance(track_payload, dict) else None)
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

        next_offset = self._parse_next_offset(str(payload.get("next") or ""))
        total_tracks = self._safe_int(payload.get("total"))
        if total_tracks is None:
            total_tracks = self._safe_int(cursor.get("total"))

        if next_offset is None:
            return queries, None

        next_cursor = {
            "kind": kind,
            "entity_id": entity_id,
            "display_title": display_title or entity_id,
            "offset": next_offset,
            "total": total_tracks,
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
                "total_tracks": 1,
                "partial": False,
                "partial_reason": None,
            }

        limit = max(1, int(initial_limit))

        if reference.kind == "artist":
            display_title = await self._get_artist_name(reference.entity_id)
            initial_queries = await self._get_artist_top_track_queries(
                reference.entity_id,
                limit=limit,
            )
            return {
                "kind": "artist",
                "display_title": display_title,
                "initial_queries": initial_queries[:limit],
                "deferred_cursor": None,
                "total_tracks": len(initial_queries),
                "partial": False,
                "partial_reason": None,
            }

        if reference.kind == "playlist":
            playlist_payload = await self._get_playlist_payload(reference.entity_id)
            display_title = str(playlist_payload.get("display_title") or "").strip() or reference.entity_id
            bootstrap_items = playlist_payload.get("items")
            bootstrap_offset = self._safe_int(playlist_payload.get("offset")) or 0
            next_offset = self._safe_int(playlist_payload.get("next_offset"))
            total_tracks = self._safe_int(playlist_payload.get("total"))

            initial_queries, consumed_items = self._playlist_items_to_queries(
                bootstrap_items,
                limit=limit,
            )
            current_offset = max(0, bootstrap_offset) + consumed_items
            bootstrap_items_count = (
                len(bootstrap_items) if isinstance(bootstrap_items, list) else 0
            )

            has_more_items = self._playlist_has_more_items(
                consumed_items=consumed_items,
                bootstrap_items_count=bootstrap_items_count,
                current_offset=current_offset,
                total_tracks=total_tracks,
                next_offset=next_offset,
            )

            deferred_cursor: dict | None = None
            partial = False
            partial_reason: str | None = None

            if len(initial_queries) >= limit:
                if has_more_items:
                    deferred_cursor = {
                        "kind": "playlist",
                        "entity_id": reference.entity_id,
                        "display_title": display_title,
                        "offset": current_offset,
                        "total": total_tracks,
                    }
                return {
                    "kind": "playlist",
                    "display_title": display_title,
                    "initial_queries": initial_queries[:limit],
                    "deferred_cursor": deferred_cursor,
                    "total_tracks": total_tracks,
                    "partial": False,
                    "partial_reason": None,
                }

            if has_more_items:
                deferred_cursor = {
                    "kind": "playlist",
                    "entity_id": reference.entity_id,
                    "display_title": display_title,
                    "offset": current_offset,
                    "total": total_tracks,
                }
                try:
                    while deferred_cursor is not None and len(initial_queries) < limit:
                        remaining = limit - len(initial_queries)
                        batch_queries, deferred_cursor = await self.fetch_deferred_queries(
                            deferred_cursor,
                            batch_size=min(self.MAX_PAGE_LIMIT, remaining),
                        )
                        if batch_queries:
                            initial_queries.extend(batch_queries)
                except SpotifyApiError as exc:
                    if not initial_queries:
                        raise
                    partial = True
                    partial_reason = self._build_partial_reason(exc)
                    deferred_cursor = None

            return {
                "kind": "playlist",
                "display_title": display_title,
                "initial_queries": initial_queries[:limit],
                "deferred_cursor": deferred_cursor,
                "total_tracks": total_tracks,
                "partial": partial,
                "partial_reason": partial_reason,
            }

        display_title = await self._get_album_name(reference.entity_id)
        cursor: dict | None = {
            "kind": "album",
            "entity_id": reference.entity_id,
            "display_title": display_title,
            "offset": 0,
            "total": None,
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
            "kind": "album",
            "display_title": display_title,
            "initial_queries": initial_queries[:limit],
            "deferred_cursor": cursor,
            "total_tracks": None,
            "partial": False,
            "partial_reason": None,
        }
