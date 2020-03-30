import asyncio
import logging
import os
import sys
import traceback
from os import listdir
from os.path import isfile, join

from persiantools.digits import en_to_fa
from persiantools.jdatetime import JalaliDate, JalaliDateTime
from pymongo import MongoClient
from pytz import timezone
from telethon import TelegramClient, events
from telethon.errors.rpcerrorlist import FloodWaitError
from telethon.events.messagedeleted import MessageDeleted
from telethon.events.messageedited import MessageEdited
# from telethon.tl.custom.message import Message
from telethon.events.newmessage import NewMessage
from telethon.tl.functions.channels import CreateChannelRequest
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.tl.types import MessageService

import sessions.aes as aes

iran_tz = timezone('Iran')

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)
# ******************************************************************************** #

db_client = MongoClient(os.environ.get('DB_URI'))
db = db_client['channeller']
db_users = db['users']


# ******************************************************************************** #


class AutoChannel:
    def __init__(self, channel, origin, messages_map):
        self.channel = channel
        self.origin = origin
        self.messages_map = messages_map


class Telegram:
    def __init__(self):
        self.client = None
        self.db_user = None
        self.db_id = None
        self.my_info = None
        self.me = None
        self.auto_channels: [AutoChannel] = []

    async def init(self):
        await aes.decrypt_sessions()

        session_file = [f for f in listdir('.') if isfile(join('.', f)) and f.endswith('.session')][0][
                       :-len('.session')]

        self.client = TelegramClient(session_file, int(os.environ.get('API_ID')), os.environ.get('API_HASH'))
        # noinspection PyUnresolvedReferences
        await self.client.start()

        # Getting information about yourself
        my_info = self.my_info = await self.client.get_me()

        # noinspection PyTypeChecker
        self.me = await self.client.get_entity(my_info.id)
        print(self.me)

        print(f'Signed in as @{my_info.username} (+{my_info.phone})')

        self.db_user = db_users.find_one({'id': my_info.id}, {'autoChannels': True})

        if self.db_user:
            self.db_id = self.db_user['_id']
            for db_auto_channel in self.db_user['autoChannels']:
                messages_map = {}
                for msg_map in db_auto_channel['messagesMap']:
                    messages_map[msg_map['origin']] = msg_map['channel']

                self.auto_channels.append(AutoChannel(
                    await self.client.get_entity(db_auto_channel['channel']),
                    # telethon.errors.rpcerrorlist.ChannelPrivateError: The channel specified is private and you lack permission to access it. Another reason may be that you were banned from it (caused by GetChannelsRequest)
                    await self.client.get_entity(db_auto_channel['origin']),
                    messages_map
                ))
        else:
            self.db_user = {
                'id': my_info.id,
                'phone': my_info.phone,
                'username': my_info.username,
                'first_name': my_info.first_name,
                'last_name': my_info.last_name,
                'autoChannels': [],
            }
            db_insert = db_users.insert_one(self.db_user)

            self.db_id = self.db_user['_id'] = db_insert.inserted_id

    async def serve(self):
        for auto_channel in self.auto_channels:
            await self.set_event_handlers(auto_channel.channel, auto_channel.origin, auto_channel.messages_map)

        @self.client.on(events.NewMessage(chats=self.me, from_users=self.me, incoming=False,
                                          pattern=r'^/(\w+(-\w+)*)$'))  # sample match: "/do-task"
        async def command_handler(new_command: NewMessage.Event):
            print(new_command.raw_text)
            if new_command.pattern_match.group(1) == 'make-it-my-channel':
                await self.client.send_message(self.me,
                                               "**OK! I'm ready. Are you ready too?**\n\n"
                                               "Forward a message from that chat (channel, group, etc.). I'll make it a "
                                               "**your own channel**! 😊 (go and say my dad grew me up!).\n\n"
                                               "After that com back here!")

            self.client.add_event_handler(
                self.forward_handler,
                events.NewMessage(chats=self.me, from_users=self.me, outgoing=False, forwards=True)
            )

    async def forward_handler(self, new_forward: NewMessage.Event):
        try:
            print(type(new_forward))
            await new_forward.reply("👌")

            forward_from = await self.client.get_entity(new_forward.message.forward.chat.id)
            print(forward_from)

            channel = None
            for auto_channel in self.auto_channels:
                if auto_channel.origin.id == forward_from.id:
                    channel = auto_channel.channel
                    break

            invite_link = ''
            if channel:
                try:
                    # noinspection PyTypeChecker
                    invite_link = (await self.client(ExportChatInviteRequest(channel))).link
                except Exception as e:
                    print(e)

            if not invite_link:
                created_private_channel = await self.client(
                    CreateChannelRequest(forward_from.title + '*', '', megagroup=False))
                channel_id = created_private_channel.chats[0].id
                new_channel_access_hash = created_private_channel.chats[0].access_hash
                print(new_channel_access_hash, channel_id)

                channel = await self.client.get_entity(channel_id)

                auto_channel = AutoChannel(channel, forward_from, {})
                self.auto_channels.append(auto_channel)

                db_users.update_one({'_id': self.db_id}, {'$push': {'autoChannels': {
                    'origin': forward_from.id,
                    'channel': channel_id,
                    'messagesMap': [],
                }}})

                # noinspection PyTypeChecker
                invite_link = (await self.client(ExportChatInviteRequest(channel))).link
                print(invite_link)
                await self.client.send_message(
                    self.me, "**Your channel is created, but it's not ready yet:**\n%s\n\n"
                        "Go [there](%s) and see the magic process. You should be patient until reach the"
                        "most recent post __(to estimate when, see stamped date on the foot of each "
                        "incoming post)__." % (invite_link, invite_link))

                # pull history from original chat:
                reversed_messages = []
                # Avoid `FloodWaitError` (70 messages per each 5 minutes MAX!):
                async for message in self.client.iter_messages(forward_from, limit=600):
                    if type(message) == MessageService:
                        print(message)
                        continue
                    if message.date < new_forward.message.forward.date:
                        break
                    reversed_messages.append(message)

                # send history for new channel:
                messages = reversed(reversed_messages)
                pushed_to_map = []

                try:
                    i = 0
                    for message in messages:
                        i += 1
                        j = i / 2
                        while j.is_integer():
                            print(i)
                            await asyncio.sleep(0.5)
                            j = j / 2

                        date_time_stamp = '`' + en_to_fa(  # Use timestamp-converting to avoid time-zone issues:
                            JalaliDateTime.fromtimestamp(message.date.timestamp()).strftime('%Y/%m/%d %H:%M')) + '`'

                        sent_message = await self.send_message(
                            date_time_stamp, message, auto_channel.messages_map, channel, forward_from, False)

                        pushed_to_map.append({'origin': message.id, 'channel': sent_message.id})

                    db_users.update_one({
                        '_id': self.db_id,
                        'autoChannels': {'$elemMatch': {'channel': channel.id}}
                    }, {'$push': {
                        'autoChannels.$.messagesMap': {'$each': pushed_to_map}
                    }})
                except FloodWaitError:
                    print(traceback.format_exc(), file=sys.stderr)
                    return

            # noinspection PyUnboundLocalVariable
            await self.set_event_handlers(channel, forward_from, auto_channel.messages_map)

            self.client.remove_event_handler(forward_from)

            await self.client.send_message(self.me, '**Your channel is ready!** 👇\n' + invite_link)
        except:
            print(traceback.format_exc(), file=sys.stderr)
            try:
                await self.client.send_message(self.me, 'Unexpected error # 1894')
            except:
                print(traceback.format_exc(), file=sys.stderr)

    async def send_message(self, stamp, message, messages_map, channel, origin, register_to_db=True):
        original_text = message.text
        message.text = original_text + '\n\n' + stamp

        max_allowed_message_size = 1024 if message.media else 4096
        date_time_stamp_excluded = len(message.raw_text) > max_allowed_message_size

        if date_time_stamp_excluded:
            message.text = original_text

        reply_to_msg_id = message.reply_to_msg_id
        sent_message = None
        if message.is_reply and reply_to_msg_id:
            if reply_to_msg_id in messages_map:
                sent_message = await self.client.send_message(
                    channel, message, reply_to=messages_map[reply_to_msg_id])
            else:
                reply_to_phrase = \
                    '__reply: https://t.me/c/%s/%s__' % (origin.id, reply_to_msg_id)

                pseudo_original_text = message.text  # maybe date_time_stamp has been included, already
                message.text = reply_to_phrase + '\n\n' + pseudo_original_text
                if len(message.raw_text) > max_allowed_message_size:
                    message.text = pseudo_original_text
                    await self.client.send_message(channel, reply_to_phrase)

        if not sent_message:
            sent_message = await self.client.send_message(channel, message)

        messages_map[message.id] = sent_message.id

        if register_to_db:
            db_users.update_one({
                '_id': self.db_id,
                'autoChannels': {'$elemMatch': {'channel': channel.id}}
            }, {'$push': {
                'autoChannels.$.messagesMap': {'origin': message.id, 'channel': sent_message.id}
            }})

        if date_time_stamp_excluded:
            await self.client.send_message(channel, stamp)

        return sent_message

    async def set_event_handlers(self, channel, origin, messages_map):
        @self.client.on(events.NewMessage(chats=origin))
        async def channeller_new(new_message_event: NewMessage.Event):
            message = new_message_event.message
            if type(message) == MessageService:
                print(message)
                return

            print(message.text)
            # Unlike `JalaliDateTime`, `JalaliDate` doesn't need timestamp-converting
            date_stamp = f'`{en_to_fa(JalaliDate(message.date).strftime("%Y/%m/%d"))}`'
            await self.send_message(date_stamp, message, messages_map, channel, origin)

        # noinspection PyShadowingNames
        @self.client.on(events.MessageEdited(chats=origin))
        async def channeller_edit(edit_event: MessageEdited.Event):
            print('Message', edit_event.id, 'changed at', edit_event.date)
            message = edit_event.message
            if type(message) == MessageService or message.id not in messages_map:
                print(message)
                return

            print(message.text)

            # old_message = await self.client.get_messages(channel, ids=messages_map[message.id])

            new_text = message.text
            stamp = f'`{en_to_fa(JalaliDate(message.date).strftime("%Y/%m/%d"))}`'
            message.text = new_text + '\n\n' + stamp

            max_allowed_message_size = 1024 if message.media else 4096
            if len(message.raw_text) > max_allowed_message_size:
                message.text = new_text
            # message.id = messages_map[message.id]
            await self.client.edit_message(channel, messages_map[message.id],
                                           text=message.text,
                                           parse_mode=message.client.parse_mode,
                                           link_preview=message.web_preview,
                                           file=message.file,
                                           # force_document=message.force_document,
                                           buttons=message.buttons,
                                           # schedule=message.schedule,
                                           )

        # noinspection PyShadowingNames
        @self.client.on(events.MessageDeleted(chats=origin))
        async def channeller_delete(delete_event: MessageDeleted.Event):
            message_ids = []
            for msg_id in delete_event.deleted_ids:
                message_ids.append(messages_map[msg_id])
                print('Message', msg_id, 'was deleted in', delete_event.chat_id)

            print(delete_event)

            await self.client.delete_messages(channel, message_ids)
