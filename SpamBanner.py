from logging import getLogger, INFO
import re
import discord
from datetime import datetime, UTC

LINK_REGEX = re.compile(r'https?://\S+')

link_message_cache = {}

spam_window = 20
spam_threshold = 4

logger = getLogger(__name__)

async def check_and_ban_link_spammer(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    if not LINK_REGEX.search(message.content):
        return

    now = datetime.now(UTC)
    user_id = message.author.id
    msg_data = (now, message.content, message)

    user_cache = link_message_cache.setdefault(user_id, [])
    user_cache.append(msg_data)

    link_message_cache[user_id] = [
        (ts, content, msg) for ts, content, msg in user_cache
        if (now - ts).total_seconds() <= spam_window
    ]

    matches = [
        msg for ts, content, msg in link_message_cache[user_id]
        if content == message.content
    ]

    if len(matches) >= spam_threshold:
        for msg in matches:
            try:
                await msg.delete()
            except discord.Forbidden:
                pass
        try:
            await message.guild.ban(message.author, reason="Link spam in multiple channels")
        except discord.Forbidden:
            logger.log(msg=f"Couldn't ban {message.author} — missing permissions", level=INFO)
        link_message_cache.pop(user_id, None)
