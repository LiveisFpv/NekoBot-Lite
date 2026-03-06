from __future__ import annotations

import base64
import json
import os
import re
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
    PATHFINDER_URL = "https://api-partner.spotify.com/pathfinder/v1/query"
    PATHFINDER_QUERY_PLAYLIST_OPERATION = "queryPlaylist"
    PATHFINDER_QUERY_PLAYLIST_HASH = "2888863ae48f035d0177d73c88f389e7946a95d49a8883a26e86aebd02f2ed24"
    _INITIAL_STATE_RE = re.compile(
        r'<script id="initialState"[^>]*>(.*?)</script>',
        re.IGNORECASE | re.DOTALL,
    )
    _OG_TITLE_RE = re.compile(
        r'<meta property="og:title" content="([^"]+)"',
        re.IGNORECASE,
    )
    _MUSIC_SONG_RE = re.compile(
        r'<meta name="music:song" content="([^"]+)"',
        re.IGNORECASE,
    )

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

    async def _post_json(self, url: str, data: dict) -> dict:
        headers = await self._auth_headers()
        try:
            payload = await self.http_service.post_json(url, data=data, headers=headers)
        except Exception as exc:
            details = f"{type(exc).__name__}: {exc}"
            if isinstance(exc, HttpRequestError):
                details = f"{type(exc).__name__}: status={exc.status}, body={exc.body[:300]}"
            raise SpotifyApiError(
                f"Spotify API request failed: {url} ({details})"
            ) from exc
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _is_forbidden_error(exc: Exception) -> bool:
        cause = getattr(exc, "__cause__", None)
        return isinstance(cause, HttpRequestError) and int(cause.status) == 403

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
    def _extract_playlist_queries_from_initial_state(
        raw_initial_state: str,
        playlist_id: str,
        *,
        limit: int,
    ) -> tuple[str, list[str]]:
        if not raw_initial_state:
            return playlist_id, []

        try:
            decoded = base64.b64decode(raw_initial_state + "===")
            state = json.loads(decoded.decode("utf-8", errors="ignore"))
        except Exception:
            return playlist_id, []

        playlist_uri = f"spotify:playlist:{playlist_id}"
        entities = state.get("entities") or {}
        items = entities.get("items") if isinstance(entities, dict) else {}
        playlist_payload = items.get(playlist_uri) if isinstance(items, dict) else {}
        if not isinstance(playlist_payload, dict):
            return playlist_id, []

        display_title = str(playlist_payload.get("name") or "").strip() or playlist_id
        content = playlist_payload.get("content") or {}
        content_items = content.get("items") if isinstance(content, dict) else []
        if not isinstance(content_items, list):
            return display_title, []

        queries: list[str] = []
        for entry in content_items:
            item_v2 = entry.get("itemV2") if isinstance(entry, dict) else None
            track_data = item_v2.get("data") if isinstance(item_v2, dict) else None
            if not isinstance(track_data, dict):
                continue

            name = str(track_data.get("name") or "").strip()
            artists: list[str] = []
            artists_payload = track_data.get("artists")
            artists_items = artists_payload.get("items") if isinstance(artists_payload, dict) else []
            if isinstance(artists_items, list):
                for artist_entry in artists_items:
                    if not isinstance(artist_entry, dict):
                        continue
                    profile = artist_entry.get("profile")
                    artist_name = (
                        str(profile.get("name") or "").strip()
                        if isinstance(profile, dict)
                        else ""
                    )
                    if not artist_name:
                        artist_name = str(artist_entry.get("name") or "").strip()
                    if artist_name:
                        artists.append(artist_name)

            query = SpotifyService.build_search_query(name, artists)
            if query:
                queries.append(query)
            if len(queries) >= limit:
                break

        return display_title, queries

    @staticmethod
    def _track_query_from_item_v2(item_v2: dict | None) -> str:
        track_data = item_v2.get("data") if isinstance(item_v2, dict) else None
        if not isinstance(track_data, dict):
            return ""

        name = str(track_data.get("name") or "").strip()
        artists: list[str] = []
        artists_payload = track_data.get("artists")
        artists_items = artists_payload.get("items") if isinstance(artists_payload, dict) else []
        if isinstance(artists_items, list):
            for artist_entry in artists_items:
                if not isinstance(artist_entry, dict):
                    continue
                profile = artist_entry.get("profile")
                artist_name = (
                    str(profile.get("name") or "").strip()
                    if isinstance(profile, dict)
                    else ""
                )
                if not artist_name:
                    artist_name = str(artist_entry.get("name") or "").strip()
                if artist_name:
                    artists.append(artist_name)

        return SpotifyService.build_search_query(name, artists)

    async def _fetch_playlist_queries_via_pathfinder(
        self,
        playlist_id: str,
        *,
        limit: int | None = None,
    ) -> tuple[str, list[str]]:
        playlist_uri = f"spotify:playlist:{playlist_id}"
        offset = 0
        page_limit = 50
        max_items = None if limit is None else max(1, int(limit))
        display_title = playlist_id
        queries: list[str] = []
        seen: set[str] = set()

        while True:
            payload = await self._post_json(
                self.PATHFINDER_URL,
                data={
                    "operationName": self.PATHFINDER_QUERY_PLAYLIST_OPERATION,
                    "variables": {
                        "uri": playlist_uri,
                        "offset": offset,
                        "limit": page_limit,
                    },
                    "extensions": {
                        "persistedQuery": {
                            "version": 1,
                            "sha256Hash": self.PATHFINDER_QUERY_PLAYLIST_HASH,
                        }
                    },
                },
            )

            data_payload = payload.get("data") if isinstance(payload, dict) else None
            playlist_payload = (
                data_payload.get("playlistV2") if isinstance(data_payload, dict) else None
            )
            if not isinstance(playlist_payload, dict):
                break

            current_title = str(playlist_payload.get("name") or "").strip()
            if current_title:
                display_title = current_title

            content = playlist_payload.get("content") or {}
            items = content.get("items") if isinstance(content, dict) else []
            if isinstance(items, list):
                for entry in items:
                    item_v2 = entry.get("itemV2") if isinstance(entry, dict) else None
                    query = self._track_query_from_item_v2(item_v2)
                    if not query or query in seen:
                        continue
                    seen.add(query)
                    queries.append(query)
                    if max_items is not None and len(queries) >= max_items:
                        return display_title, queries

            paging_info = content.get("pagingInfo") if isinstance(content, dict) else {}
            next_offset = paging_info.get("nextOffset") if isinstance(paging_info, dict) else None
            if not isinstance(next_offset, int) or next_offset <= offset:
                break
            offset = next_offset

        return display_title, queries

    @classmethod
    def _extract_playlist_title_from_html(cls, html: str, fallback: str) -> str:
        match = cls._OG_TITLE_RE.search(html or "")
        if not match:
            return fallback
        title = str(match.group(1) or "").strip()
        return title or fallback

    async def _resolve_public_playlist_via_web(
        self,
        playlist_id: str,
        *,
        limit: int,
    ) -> tuple[str, list[str]]:
        page_url = f"https://open.spotify.com/playlist/{playlist_id}"
        try:
            page_html = await self.http_service.get_text(page_url)
        except Exception as exc:
            raise SpotifyApiError(
                "Spotify web fallback request failed: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        display_title = self._extract_playlist_title_from_html(page_html, playlist_id)

        initial_state_match = self._INITIAL_STATE_RE.search(page_html or "")
        if initial_state_match:
            display_title, queries = self._extract_playlist_queries_from_initial_state(
                str(initial_state_match.group(1) or "").strip(),
                playlist_id,
                limit=limit,
            )
            if queries:
                return display_title, queries

        track_urls = self._MUSIC_SONG_RE.findall(page_html or "")
        queries: list[str] = []
        for track_url in track_urls[:limit]:
            try:
                track_ref = self.parse_spotify_url(track_url)
                if track_ref.kind != "track":
                    continue
                payload = await self._get_json(f"{self.API_BASE}/tracks/{track_ref.entity_id}")
            except Exception:
                continue
            query = self._track_to_query(payload)
            if query:
                queries.append(query)
            if len(queries) >= limit:
                break

        return display_title, queries

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
        if kind == "prefetched":
            all_queries_raw = cursor.get("queries")
            if not isinstance(all_queries_raw, list):
                return [], None
            all_queries = [str(item or "").strip() for item in all_queries_raw if str(item or "").strip()]
            index = max(0, int(cursor.get("index") or 0))
            page_limit = max(1, min(int(batch_size), self.MAX_PAGE_LIMIT))
            next_index = min(len(all_queries), index + page_limit)
            current_batch = all_queries[index:next_index]
            if next_index >= len(all_queries):
                return current_batch, None
            return current_batch, {
                "kind": "prefetched",
                "queries": all_queries,
                "index": next_index,
                "display_title": str(cursor.get("display_title") or "").strip(),
            }

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

        if reference.kind == "artist":
            limit = max(1, int(initial_limit))
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
            }

        if reference.kind == "playlist":
            limit = max(1, int(initial_limit))
            try:
                display_title = await self._get_playlist_name(reference.entity_id)
            except SpotifyApiError as exc:
                if not self._is_forbidden_error(exc):
                    raise
                try:
                    pf_title, pf_queries = await self._fetch_playlist_queries_via_pathfinder(
                        reference.entity_id,
                        limit=None,
                    )
                except SpotifyApiError:
                    pf_title, pf_queries = "", []
                if pf_queries:
                    initial = pf_queries[:limit]
                    deferred_cursor = (
                        {
                            "kind": "prefetched",
                            "queries": pf_queries,
                            "index": len(initial),
                            "display_title": pf_title or reference.entity_id,
                        }
                        if len(pf_queries) > len(initial)
                        else None
                    )
                    return {
                        "kind": "playlist",
                        "display_title": pf_title or reference.entity_id,
                        "initial_queries": initial,
                        "deferred_cursor": deferred_cursor,
                        "fallback_mode": "pathfinder",
                    }
                display_title, web_queries = await self._resolve_public_playlist_via_web(
                    reference.entity_id,
                    limit=limit,
                )
                if not web_queries:
                    raise SpotifyApiError(
                        "Spotify playlist is inaccessible via API (403) "
                        "and web fallback returned no tracks."
                    ) from exc
                return {
                    "kind": "playlist",
                    "display_title": display_title,
                    "initial_queries": web_queries[:limit],
                    "deferred_cursor": None,
                    "fallback_mode": "web",
                }
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

        try:
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
        except SpotifyApiError as exc:
            if reference.kind != "playlist" or not self._is_forbidden_error(exc):
                raise

            try:
                pf_title, pf_queries = await self._fetch_playlist_queries_via_pathfinder(
                    reference.entity_id,
                    limit=None,
                )
            except SpotifyApiError:
                pf_title, pf_queries = "", []
            if pf_queries:
                initial = pf_queries[:limit]
                deferred_cursor = (
                    {
                        "kind": "prefetched",
                        "queries": pf_queries,
                        "index": len(initial),
                        "display_title": display_title or pf_title or reference.entity_id,
                    }
                    if len(pf_queries) > len(initial)
                    else None
                )
                return {
                    "kind": "playlist",
                    "display_title": display_title or pf_title or reference.entity_id,
                    "initial_queries": initial,
                    "deferred_cursor": deferred_cursor,
                    "fallback_mode": "pathfinder",
                }

            web_title, web_queries = await self._resolve_public_playlist_via_web(
                reference.entity_id,
                limit=limit,
            )
            merged: list[str] = []
            seen: set[str] = set()
            for item in initial_queries + web_queries:
                item_text = str(item or "").strip()
                if not item_text or item_text in seen:
                    continue
                seen.add(item_text)
                merged.append(item_text)
                if len(merged) >= limit:
                    break
            if not merged:
                raise SpotifyApiError(
                    "Spotify playlist is inaccessible via API (403) "
                    "and web fallback returned no tracks."
                ) from exc
            return {
                "kind": "playlist",
                "display_title": display_title or web_title,
                "initial_queries": merged,
                "deferred_cursor": None,
                "fallback_mode": "web",
            }

        if reference.kind == "playlist" and not initial_queries:
            try:
                pf_title, pf_queries = await self._fetch_playlist_queries_via_pathfinder(
                    reference.entity_id,
                    limit=None,
                )
            except SpotifyApiError:
                pf_title, pf_queries = "", []
            if pf_queries:
                initial = pf_queries[:limit]
                deferred_cursor = (
                    {
                        "kind": "prefetched",
                        "queries": pf_queries,
                        "index": len(initial),
                        "display_title": display_title or pf_title or reference.entity_id,
                    }
                    if len(pf_queries) > len(initial)
                    else None
                )
                return {
                    "kind": "playlist",
                    "display_title": display_title or pf_title or reference.entity_id,
                    "initial_queries": initial,
                    "deferred_cursor": deferred_cursor,
                    "fallback_mode": "pathfinder",
                }

            try:
                web_title, web_queries = await self._resolve_public_playlist_via_web(
                    reference.entity_id,
                    limit=limit,
                )
            except SpotifyApiError:
                web_title, web_queries = "", []

            if web_queries:
                return {
                    "kind": "playlist",
                    "display_title": display_title or web_title,
                    "initial_queries": web_queries[:limit],
                    "deferred_cursor": None,
                    "fallback_mode": "web",
                }

        return {
            "kind": reference.kind,
            "display_title": display_title,
            "initial_queries": initial_queries[:limit],
            "deferred_cursor": cursor,
        }
