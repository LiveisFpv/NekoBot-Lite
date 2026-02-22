import asyncio
from utils.utils import log


class MediaPlayer:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.queue_next = asyncio.Queue()
        self.history = asyncio.LifoQueue()
        self.history_next = asyncio.LifoQueue()
        self.loop = False
        self.loop_playlist = False

    async def add_to_queue(self, url):
        if not self.queue.empty():
            await self.queue_next.put(url)
        await self.queue.put(url)
        await log(f"INFO: Added to queue: {url}")

    async def get_next_song(self):
        next_song = None
        if self.loop:
            song = await self.history.get()
            if not self.history_next.empty():
                next_song = await self.history_next.get()
                await self.history_next.put(next_song)
            await self.history.put(song)
            return song, next_song

        if not self.queue.empty():
            song = await self.queue.get()
            if not self.queue_next.empty():
                next_song = await self.queue_next.get()
                await self.history_next.put(next_song)
            await self.history.put(song)
            return song, next_song

        return None, None

    async def delete_all_tracks(self):
        while not self.queue.empty():
            await self.queue.get()
        while not self.history.empty():
            await self.history.get()
        while not self.queue_next.empty():
            await self.queue_next.get()
        while not self.history_next.empty():
            await self.history_next.get()

    async def get_previous_song(self):
        if not self.history.empty():
            song = await self.history.get()
            await self.queue.put(song)
            return song
        return None
