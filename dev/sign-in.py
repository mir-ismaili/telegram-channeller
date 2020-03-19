import os

from telethon import TelegramClient

# These example values won't work. You must get your own api_id and
# api_hash from https://my.telegram.org, under API Development.
api_id = int(os.environ.get('API_ID'))
api_hash = os.environ.get('API_HASH')

sessionFileName = input("Enter a name for this user (e.g. user's id). This would be the name of session file: ")

client = TelegramClient(sessionFileName, api_id, api_hash)
client.start()
