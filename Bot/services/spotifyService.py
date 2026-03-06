from __future__ import annotations

import base64
import html
import json
import os
import re
from dataclasses import dataclass
from urllib.parse import quote, urlparse

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
    MAX_FALLBACK_LIMIT = 200

    _OG_TITLE_RE = re.compile(
        r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    _SCRIPT_TAG_RE = re.compile(
        r'<script[^>]*id=["\'](?P<id>initialState|initial-state|__NEXT_DATA__)["\'][^>]*>(?P<content>.*?)</script>',
        re.IGNORECASE | re.DOTALL,
    )
    _JSON_LD_RE = re.compile(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(?P<content>.*?)</script>',
        re.IGNORECASE | re.DOTALL,
    )
    _TRACK_URL_RE = re.compile(r"https://open\.spotify\.com/track/[A-Za-z0-9]+", re.IGNORECASE)

    def __init__(
        self,
        *,
        http_service: HttpService | None = None,
    ):
        self.http_service = http_service or HttpService(
            proxy_url=self._get_env_str("SPOTIFY_PROXY_URL") or None,
            proxy_username=self._get_env_str("SPOTIFY_PROXY_USERNAME") or None,
            proxy_password=os.getenv("SPOTIFY_PROXY_PASSWORD", ""),
            timeout_seconds=15,
        )

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
        candidate = (value or "").strip()

        if candidate.startswith("spotify:"):
            parts = [item.strip() for item in candidate.split(":") if item.strip()]
            if len(parts) >= 3:
                kind = parts[1].lower()
                entity_id = parts[2]
                if kind in {"track", "playlist", "album", "artist"} and entity_id:
                    return SpotifyEntityRef(kind=kind, entity_id=entity_id)

        parsed = urlparse(candidate)
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

    @classmethod
    def _extract_title_from_html(cls, html_text: str, fallback: str) -> str:
        match = cls._OG_TITLE_RE.search(html_text or "")
        if not match:
            return fallback
        title = str(match.group(1) or "").strip()
        return title or fallback

    @staticmethod
    def _try_parse_json(payload: str) -> object | None:
        text = str(payload or "").strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
            return None

    @classmethod
    def _decode_script_payload(cls, payload: str) -> object | None:
        raw = html.unescape(str(payload or "")).strip()
        if not raw:
            return None

        parsed = cls._try_parse_json(raw)
        if parsed is not None:
            return parsed

        compact = re.sub(r"\s+", "", raw)
        if not compact:
            return None

        for suffix in ("", "=", "==", "==="):
            try:
                decoded = base64.b64decode(compact + suffix)
            except Exception:
                continue
            parsed = cls._try_parse_json(decoded.decode("utf-8", errors="ignore"))
            if parsed is not None:
                return parsed
        return None

    @staticmethod
    def _artist_name_from_node(node: object) -> str:
        if isinstance(node, str):
            return node.strip()
        if not isinstance(node, dict):
            return ""

        name = str(node.get("name") or "").strip()
        if name:
            return name

        profile = node.get("profile")
        if isinstance(profile, dict):
            profile_name = str(profile.get("name") or "").strip()
            if profile_name:
                return profile_name
        return ""

    @classmethod
    def _extract_artist_names(cls, raw: object) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()

        def push(value: str) -> None:
            item = str(value or "").strip()
            if not item or item in seen:
                return
            seen.add(item)
            names.append(item)

        def walk(node: object) -> None:
            if isinstance(node, str):
                push(node)
                return

            if isinstance(node, list):
                for item in node:
                    walk(item)
                return

            if not isinstance(node, dict):
                return

            direct_name = cls._artist_name_from_node(node)
            if direct_name:
                push(direct_name)

            for key in ("items", "artists", "artist", "byArtist", "contributors"):
                if key in node:
                    walk(node.get(key))

        walk(raw)
        return names

    @classmethod
    def _candidate_to_query(cls, candidate: dict) -> str:
        if not isinstance(candidate, dict):
            return ""
        if bool(candidate.get("is_local") or candidate.get("isLocal") or candidate.get("local")):
            return ""

        name = str(candidate.get("name") or candidate.get("title") or "").strip()
        if not name:
            return ""

        type_value = str(candidate.get("type") or candidate.get("__typename") or "").strip().lower()
        if type_value:
            if "track" not in type_value and type_value not in {"song", "audio"}:
                return ""
        else:
            track_hints = {
                "duration_ms",
                "duration",
                "track_number",
                "disc_number",
                "preview_url",
                "is_playable",
            }
            if not any(key in candidate for key in track_hints):
                return ""

        artists: list[str] = []
        for key in ("artists", "artist", "byArtist"):
            if key in candidate:
                artists.extend(cls._extract_artist_names(candidate.get(key)))

        dedup_artists: list[str] = []
        seen: set[str] = set()
        for item in artists:
            if item in seen:
                continue
            seen.add(item)
            dedup_artists.append(item)

        return cls.build_search_query(name, dedup_artists)

    @classmethod
    def _extract_queries_from_json(cls, payload: object, *, limit: int) -> list[str]:
        queries: list[str] = []
        seen: set[str] = set()

        def push(query: str) -> None:
            text = str(query or "").strip()
            if not text or text in seen:
                return
            seen.add(text)
            queries.append(text)

        def walk(node: object) -> None:
            if len(queries) >= limit:
                return

            if isinstance(node, list):
                for item in node:
                    walk(item)
                    if len(queries) >= limit:
                        return
                return

            if not isinstance(node, dict):
                return

            query = cls._candidate_to_query(node)
            if query:
                push(query)
                if len(queries) >= limit:
                    return

            for value in node.values():
                walk(value)
                if len(queries) >= limit:
                    return

        walk(payload)
        return queries

    @classmethod
    def _extract_track_urls_from_html(cls, html_text: str, *, limit: int) -> list[str]:
        if not html_text:
            return []
        urls: list[str] = []
        seen: set[str] = set()
        for match in cls._TRACK_URL_RE.findall(html_text):
            value = str(match or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            urls.append(value)
            if len(urls) >= limit:
                break
        return urls

    async def _query_from_track_oembed(self, track_url: str) -> str:
        oembed_url = f"https://open.spotify.com/oembed?url={quote(track_url, safe='')}"
        payload = await self.http_service.get_json(oembed_url)
        title = str(payload.get("title") or "").strip() if isinstance(payload, dict) else ""
        author = str(payload.get("author_name") or "").strip() if isinstance(payload, dict) else ""
        return self.build_search_query(title, [author] if author else [])

    async def _resolve_collection_via_web(
        self,
        *,
        kind: str,
        entity_id: str,
        limit: int,
    ) -> tuple[str, list[str]]:
        page_url = f"https://open.spotify.com/{kind}/{entity_id}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            page_html = await self.http_service.get_text(page_url, headers=headers)
        except Exception as exc:
            raise SpotifyApiError(
                "Spotify web fallback request failed: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        display_title = self._extract_title_from_html(page_html, entity_id)
        capped_limit = max(1, min(int(limit), self.MAX_FALLBACK_LIMIT))
        queries: list[str] = []
        seen: set[str] = set()

        for match in self._SCRIPT_TAG_RE.finditer(page_html or ""):
            payload = self._decode_script_payload(str(match.group("content") or ""))
            if payload is None:
                continue
            for query in self._extract_queries_from_json(payload, limit=capped_limit):
                if query in seen:
                    continue
                seen.add(query)
                queries.append(query)
                if len(queries) >= capped_limit:
                    return display_title, queries

        for match in self._JSON_LD_RE.finditer(page_html or ""):
            payload = self._decode_script_payload(str(match.group("content") or ""))
            if payload is None:
                continue
            for query in self._extract_queries_from_json(payload, limit=capped_limit):
                if query in seen:
                    continue
                seen.add(query)
                queries.append(query)
                if len(queries) >= capped_limit:
                    return display_title, queries

        if len(queries) >= capped_limit:
            return display_title, queries[:capped_limit]

        track_urls = self._extract_track_urls_from_html(
            page_html,
            limit=capped_limit - len(queries),
        )
        for track_url in track_urls:
            try:
                query = await self._query_from_track_oembed(track_url)
            except Exception:
                continue
            if not query or query in seen:
                continue
            seen.add(query)
            queries.append(query)
            if len(queries) >= capped_limit:
                break

        return display_title, queries[:capped_limit]

    async def resolve_for_enqueue(self, query: str, *, initial_limit: int = 100) -> dict:
        reference = self.parse_spotify_url(query)
        if reference.kind == "track":
            return {
                "kind": "track",
                "display_title": reference.entity_id,
                "initial_queries": [],
                "deferred_cursor": None,
            }

        if reference.kind not in {"playlist", "album", "artist"}:
            raise SpotifyApiError("Unsupported Spotify URL path.")

        limit = max(1, int(initial_limit))
        display_title, queries = await self._resolve_collection_via_web(
            kind=reference.kind,
            entity_id=reference.entity_id,
            limit=limit,
        )
        if not queries:
            raise SpotifyApiError(
                "Spotify web fallback returned no tracks for this collection."
            )

        return {
            "kind": reference.kind,
            "display_title": display_title or reference.entity_id,
            "initial_queries": queries[:limit],
            "deferred_cursor": None,
        }
