import asyncpraw
from Config.config import reddit_api

async def get_reddit_instance():
    reddit = asyncpraw.Reddit(
        client_id=reddit_api['client_id'],
        client_secret=reddit_api['client_secret'],
        user_agent=reddit_api['user_agent']
    )
    return reddit