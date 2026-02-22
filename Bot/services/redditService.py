import random
import asyncpraw
from Config.config import reddit_api


class RedditService:
    MEDIA_EXTENSIONS = (".jpg", ".png", ".gif")

    def __init__(self):
        self._reddit = None

    async def get_reddit_instance(self):
        if self._reddit is None:
            self._reddit = asyncpraw.Reddit(
                client_id=reddit_api["client_id"],
                client_secret=reddit_api["client_secret"],
                user_agent=reddit_api["user_agent"],
            )
        return self._reddit

    @staticmethod
    def is_media_url(url: str) -> bool:
        lowered = (url or "").lower()
        return any(ext in lowered for ext in RedditService.MEDIA_EXTENSIONS)

    async def get_random_media_submission(self, subreddit_name: str, limit: int = 100):
        reddit = await self.get_reddit_instance()
        subreddit = await reddit.subreddit(subreddit_name)
        submissions = [submission async for submission in subreddit.hot(limit=limit)]

        if not submissions:
            return None

        max_attempts = min(1000, len(submissions) * 5)
        for _ in range(max_attempts):
            candidate = random.choice(submissions)
            if self.is_media_url(candidate.url):
                return candidate

        return None
