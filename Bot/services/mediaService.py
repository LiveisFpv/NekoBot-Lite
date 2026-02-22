import asyncio
import time
from collections import deque

from utils.utils import log


class MediaPlayer:
    def __init__(self):
        self._queue = deque()
        self._history = deque()
        self.current_track = None
        self.loop = False
        self.loop_playlist = False
        self._lock = asyncio.Lock()
        self._playback_started_at = None
        self._paused_started_at = None
        self._paused_seconds_total = 0.0

    @staticmethod
    def _make_track(url: str, title: str | None = None):
        return {"url": url, "title": title}

    @staticmethod
    def get_track_title(track):
        if not track:
            return "end of playlist"
        return track.get("title") or track.get("url") or "unknown"

    async def add_to_queue(self, url: str, title: str | None = None):
        if not url:
            return
        track = self._make_track(url, title)
        async with self._lock:
            self._queue.append(track)
        await log(f"INFO: Added to queue: {track['url']}")

    async def queue_size(self) -> int:
        async with self._lock:
            return len(self._queue)

    async def has_pending_tracks(self) -> bool:
        async with self._lock:
            return bool(self._queue) or (self.loop and self.current_track is not None)

    async def peek_next_song(self):
        async with self._lock:
            return self._queue[0] if self._queue else None

    async def set_current_track_title(self, title: str):
        if not title:
            return
        async with self._lock:
            if self.current_track is not None:
                self.current_track["title"] = title

    async def set_current_track_metadata(
        self,
        title: str | None = None,
        duration_seconds: int | float | None = None,
    ):
        async with self._lock:
            if self.current_track is None:
                return
            if title:
                self.current_track["title"] = title
            if duration_seconds is not None:
                try:
                    self.current_track["duration_seconds"] = int(duration_seconds)
                except Exception:
                    self.current_track["duration_seconds"] = None

    async def begin_current_playback(self):
        async with self._lock:
            self._playback_started_at = time.monotonic()
            self._paused_started_at = None
            self._paused_seconds_total = 0.0

    async def mark_paused(self):
        async with self._lock:
            if self._playback_started_at is None:
                return
            if self._paused_started_at is None:
                self._paused_started_at = time.monotonic()

    async def mark_resumed(self):
        async with self._lock:
            if self._playback_started_at is None:
                return
            if self._paused_started_at is not None:
                self._paused_seconds_total += time.monotonic() - self._paused_started_at
                self._paused_started_at = None

    def _get_elapsed_seconds_locked(self) -> int:
        if self._playback_started_at is None:
            return 0

        now = time.monotonic()
        paused_seconds = self._paused_seconds_total
        if self._paused_started_at is not None:
            paused_seconds += now - self._paused_started_at

        elapsed = now - self._playback_started_at - paused_seconds
        return max(0, int(elapsed))

    async def get_status_snapshot(self):
        async with self._lock:
            current_title = self.get_track_title(self.current_track)
            next_track = self._queue[0] if self._queue else None
            next_title = self.get_track_title(next_track)
            queue_size = len(self._queue)
            elapsed_seconds = self._get_elapsed_seconds_locked()
            duration_seconds = None
            if self.current_track is not None:
                duration_seconds = self.current_track.get("duration_seconds")
            return current_title, next_title, queue_size, elapsed_seconds, duration_seconds

    async def get_next_song(self):
        async with self._lock:
            if self.loop and self.current_track is not None:
                next_track = self._queue[0] if self._queue else None
                return self.current_track, next_track

            if self.current_track is not None:
                self._history.append(self.current_track)
                if self.loop_playlist:
                    self._queue.append(self.current_track)

            if not self._queue:
                self.current_track = None
                self._playback_started_at = None
                self._paused_started_at = None
                self._paused_seconds_total = 0.0
                return None, None

            self.current_track = self._queue.popleft()
            self._playback_started_at = None
            self._paused_started_at = None
            self._paused_seconds_total = 0.0
            next_track = self._queue[0] if self._queue else None
            return self.current_track, next_track

    async def delete_all_tracks(self):
        async with self._lock:
            self._queue.clear()
            self._history.clear()
            self.current_track = None
            self._playback_started_at = None
            self._paused_started_at = None
            self._paused_seconds_total = 0.0

    async def get_previous_song(self):
        async with self._lock:
            if not self._history:
                return None

            previous_track = self._history.pop()
            if self.current_track is not None:
                self._queue.appendleft(self.current_track)

            self.current_track = None
            self._playback_started_at = None
            self._paused_started_at = None
            self._paused_seconds_total = 0.0
            self._queue.appendleft(previous_track)
            return previous_track
