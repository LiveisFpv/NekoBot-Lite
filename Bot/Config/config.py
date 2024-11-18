import json
try:
    reddit_api = json.load(open("./Bot/Config/reddit.json","r"))
except:
    reddit_api = json.load(open("./Bot/Config/mock_reddit.json","r"))
try:
    settings_bot = json.load(open("./Bot/Config/bot.json","r"))
except:
    settings_bot = json.load(open("./Bot/Config/mock_bot.json","r"))