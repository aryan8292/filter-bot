import asyncio
from pyrogram import Client
from database.ia_filterdb import Media
from aiohttp import web
from database.users_chats_db import db
from web import web_app
from info import LOG_CHANNEL, API_ID, API_HASH, BOT_TOKEN, PORT, BIN_CHANNEL, ADMINS, DATABASE_URL
from utils import temp, get_readable_time, save_group_settings
from typing import Union, Optional, AsyncGenerator
from pyrogram import types
import time, os, platform
from pyrogram.errors import AccessTokenExpired, AccessTokenInvalid, FloodWait
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

class Bot(Client):
    def __init__(self):
        super().__init__(
            name='Auto_Filter_Bot',
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"}
        )

    async def start(self):
        temp.START_TIME = time.time()
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
        
        # MongoDB connection
        client = MongoClient(DATABASE_URL, server_api=ServerApi('1'))
        try:
            client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print("Something went wrong while connecting to the database!", e)
            exit()
        
        # Start the bot
        await super().start()

        # Handle restart.txt logic
        if os.path.exists('restart.txt'):
            with open("restart.txt") as file:
                chat_id, msg_id = map(int, file)
            try:
                await self.edit_message_text(chat_id=chat_id, message_id=msg_id, text='Restarted Successfully!')
            except:
                pass
            os.remove('restart.txt')

        temp.BOT = self
        await Media.ensure_indexes()
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        username = '@' + me.username
        print(f"{me.first_name} is started now 🤗")
        
        # Web server setup
        app = web.AppRunner(web_app)
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()

        # Log the bot start
        try:
            await self.send_message(chat_id=LOG_CHANNEL, text=f"<b>{me.mention} Restarted! 🤖</b>")
        except:
            print("Error - Make sure bot is admin in LOG_CHANNEL, exiting now")
            exit()

        # Test message in BIN_CHANNEL
        try:
            m = await self.send_message(chat_id=BIN_CHANNEL, text="Test")
            await m.delete()
        except:
            print("Error - Make sure bot is admin in BIN_CHANNEL, exiting now")
            exit()

        # Notify admins
        for admin in ADMINS:
            await self.send_message(chat_id=admin, text=f"<b>✅ ʙᴏᴛ ʀᴇsᴛᴀʀᴛᴇᴅ</b>")

    async def stop(self, *args):
        await super().stop()
        print("Bot Stopped! Bye...")

    async def iter_messages(self: Client, chat_id: Union[int, str], limit: int, offset: int = 0) -> Optional[AsyncGenerator["types.Message", None]]:
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current + new_diff + 1)))
            for message in messages:
                yield message
                current += 1

app = Bot()

while True:
    try:
        app.run()
        break  # Exit loop if bot starts successfully
    except FloodWait as e:
        print(f"FloodWait triggered. Waiting for {e.value} seconds.")
        asyncio.run(asyncio.sleep(e.value))  # Wait for the specified time
