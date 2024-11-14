from yt_dlp import YoutubeDL
from requests import get
from discord.ext.commands import Context

async def search(ctx: Context):
    arg = ctx.message.content.split('%play')[-1].strip()
    is_playlist = "playlist" in arg
    YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': not is_playlist}
    
    with YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            # Check if the argument is a valid URL
            get(arg)
            vide = ydl.extract_info(arg, download=False)
        except:
            # If not a URL, perform a search
            vide = ydl.extract_info(f"ytsearch:{arg}", download=False)
        
        # Extract the first video URL from the search results
        if 'entries' in vide:
            video = vide['entries'][0]
            url = video.get('webpage_url')
            return url
        else:
            return None