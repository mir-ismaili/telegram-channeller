import logging
import os
import sys
import traceback
from os import listdir
from os.path import isfile, join

from persiantools.digits import en_to_fa
from persiantools.jdatetime import JalaliDate, JalaliDateTime
from pytz import timezone
from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import FloodWaitError
# from telethon.tl.custom.message import Message
from telethon.events.newmessage import NewMessage
from telethon.tl.functions.channels import CreateChannelRequest
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.tl.types import MessageService

import sessions.aes as aes

iran_tz = timezone('Iran')

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)


async def serve():
    await aes.decrypt_sessions()

    # noinspection DuplicatedCode
    session_file = [f for f in listdir('.') if isfile(join('.', f)) and f.endswith('.session')][0][:-len('.session')]

    client = TelegramClient(session_file, int(os.environ.get('API_ID')), os.environ.get('API_HASH'))

    # noinspection PyUnresolvedReferences
    await client.start()

    # Getting information about yourself
    my_info = await client.get_me()

    print(f'Signed in as @{my_info.username} (+{my_info.phone})')

    # noinspection PyTypeChecker
    me = await client.get_entity(my_info.id)
    print(me)

    @client.on(events.NewMessage(
        chats=me, from_users=me, incoming=False, pattern=r'^/(\w+(-\w+)*)$'))  # sample match: "/do-task"
    async def command_handler(event: NewMessage):
        print(event.raw_text)
        if event.pattern_match.group(1) == 'make-it-my-channel':
            await client.send_message(me,
                                      "**OK! I'm ready. Are you ready too?**\n\n"
                                      "Forward a message from that chat "
                                      "(channel, group, etc.). I'll make it a **your own channel**! 😊 (go and say "
                                      "my dad grew me up!).\n\n"
                                      "Don't forget coming back here, after that! I'll "
                                      "say you what to do.")

        @client.on(events.NewMessage(chats=me, from_users=me, outgoing=False, forwards=True))
        async def forward_handler(ev: NewMessage):
            try:
                await ev.reply("👌")

                forwarded_from = await client.get_entity(ev.message.forward.chat.id)
                print(forwarded_from)

                created_private_channel = await client(CreateChannelRequest(
                    forwarded_from.title + '*', '', megagroup=False))

                new_channel_id = created_private_channel.chats[0].id
                new_channel_access_hash = created_private_channel.chats[0].access_hash
                print(new_channel_access_hash, new_channel_id)

                new_channel = await client.get_entity(new_channel_id)

                # noinspection PyTypeChecker
                invite_link = (await client(ExportChatInviteRequest(new_channel))).link
                print(invite_link)
                await client.send_message(
                    me, "**Your channel is created, but it's not ready yet:**\n%s\n\n"
                        "Go [there](%s) and see the magic process. You should be patient until reach the"
                        "most recent post __(to estimate when, see stamped date on the foot of each "
                        "incoming post)__." % (invite_link, invite_link))

                # pull history from original chat:
                reversed_messages = []
                # Avoid `FloodWaitError` (70 messages per each 5 minutes MAX!):
                async for message in client.iter_messages(forwarded_from, limit=60):
                    if type(message) == MessageService:
                        print(message)
                        continue
                    reversed_messages.append(message)

                # send history for new channel:
                messages = reversed(reversed_messages)
                try:
                    for message in messages:
                        message.text += '\n\n`%s`' % en_to_fa(  # Use timestamp-converting to avoid time-zone issues:
                            JalaliDateTime.fromtimestamp(message.date.timestamp()).strftime('%Y/%m/%d %H:%M'))
                        await client.send_message(new_channel, message)
                except FloodWaitError:
                    print(traceback.format_exc(), file=sys.stderr)

                await ev.reply('**[Your channel](%s) is ready!**' % invite_link)

                @client.on(events.NewMessage(chats=forwarded_from))
                async def channeller(new_msg: NewMessage):
                    msg = new_msg.message
                    if type(msg) == MessageService:
                        print(msg)
                        return

                    print(msg.text)
                    # Unlike `JalaliDateTime`, `JalaliDate` doesn't need timestamp-converting
                    msg.text += f'\n\n`{en_to_fa(JalaliDate(msg.date).strftime("%Y/%m/%d"))}`'
                    await client.send_message(new_channel, msg)

                client.remove_event_handler(forward_handler)
            except:
                print(traceback.format_exc(), file=sys.stderr)
                try:
                    await client.send_message(me, 'Unexpected error # 1894')
                except:
                    print(traceback.format_exc(), file=sys.stderr)
