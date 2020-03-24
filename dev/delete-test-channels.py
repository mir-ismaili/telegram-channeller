import asyncio
import logging
import os
from os import listdir
from os.path import isfile, join

from telethon import TelegramClient
# from telethon.tl.custom.message import Message
from telethon.tl.functions.channels import DeleteChannelRequest

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)


async def run():
    session_file = [f for f in listdir('.') if isfile(join('.', f)) and f.endswith('.session')][0][:-len('.session')]
    client = TelegramClient(session_file, int(os.environ.get('API_ID')), os.environ.get('API_HASH'))

    # noinspection PyUnresolvedReferences
    await client.start()

    # Getting information about yourself
    me = await client.get_me()

    print(f'Signed in as @{me.username} (+{me.phone})')

    # You can print all the dialogs/conversations that you are part of:
    async for dialog in client.iter_dialogs():
        if dialog.name == 'test*':
            await client(DeleteChannelRequest(dialog.id))
            print(f'{dialog.name}: deleted')
        else:
            print(dialog.name)


loop = asyncio.get_event_loop()
loop.run_until_complete(run())
