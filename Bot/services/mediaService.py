import asyncio
import random
from collections import deque
from typing import Any


class MediaPlayer:
    def __init__(self):
        self._history = deque()
        self.loop = False
        self.loop_playlist = False
        self.controller_channel_id: int | None = None
        self.controller_message_id: int | None = None
        self._lock = asyncio.Lock()

    @staticmethod
    def get_track_title(track: Any) -> str:
        if not track:
            return "end of playlist"

        title = getattr(track, "title", None)
        if title:
            return str(title)

        uri = getattr(track, "uri", None)
        if uri:
            return str(uri)

        identifier = getattr(track, "identifier", None)
        if identifier:
            return str(identifier)

        return "unknown"

    @staticmethod
    def format_duration(milliseconds: int | None) -> str:
        if not milliseconds or milliseconds <= 0:
            return "00:00"

        seconds = int(milliseconds // 1000)
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            return f"{hours:02}:{minutes:02}:{sec:02}"
        return f"{minutes:02}:{sec:02}"

    async def push_history(self, track: Any):
        if track is None:
            return
        async with self._lock:
            self._history.append(track)

    async def get_previous_song(self):
        async with self._lock:
            if len(self._history) < 2:
                return None, None

            current_track = self._history.pop()
            previous_track = self._history.pop()
            return previous_track, current_track

    async def get_history_size(self) -> int:
        async with self._lock:
            return len(self._history)

    async def shuffle_queue(self, queue) -> bool:
        items = list(queue)
        if len(items) < 2:
            return False

        random.shuffle(items)
        queue.clear()
        queue.put(items)
        return True

    async def set_controller_message(self, channel_id: int | None, message_id: int | None):
        async with self._lock:
            self.controller_channel_id = channel_id
            self.controller_message_id = message_id

    async def get_controller_message(self):
        async with self._lock:
            return self.controller_channel_id, self.controller_message_id

    async def clear_controller_message(self):
        async with self._lock:
            self.controller_channel_id = None
            self.controller_message_id = None

    async def set_output_channel(self, channel_id: int | None):
        async with self._lock:
            self.controller_channel_id = channel_id

    async def get_output_channel(self) -> int | None:
        async with self._lock:
            return self.controller_channel_id

    async def set_loop_flags(self, loop: bool | None = None, loop_playlist: bool | None = None):
        async with self._lock:
            if loop is not None:
                self.loop = loop
                if loop:
                    self.loop_playlist = False
            if loop_playlist is not None:
                self.loop_playlist = loop_playlist
                if loop_playlist:
                    self.loop = False

    async def get_loop_flags(self):
        async with self._lock:
            return self.loop, self.loop_playlist

    async def reset(self, queue=None):
        async with self._lock:
            self._history.clear()
            self.loop = False
            self.loop_playlist = False
            self.controller_message_id = None
            # Keep channel id to allow follow-up messages in same channel.
        if queue is not None:
            queue.clear()

    async def get_status_snapshot(self, current_track, queue):
        queue_items = list(queue)
        next_track = queue_items[0] if queue_items else None

        current_title = self.get_track_title(current_track)
        next_title = self.get_track_title(next_track)
        queue_size = len(queue_items)

        return current_title, next_title, queue_size
