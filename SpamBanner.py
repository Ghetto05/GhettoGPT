from logging import getLogger, INFO
import re
import discord
from datetime import datetime, UTC

import WellKnown

LINK_REGEX = re.compile(r'https?://\S+')

link_message_cache = {}

spam_window = 20
spam_threshold = 4

logger = getLogger(__name__)

async def check_and_ban_link_spammer(message: discord.Message, bot: discord.Bot):
    if message.author.bot or not message.guild:
        return

    if not LINK_REGEX.search(message.content):
        return

    logger.log(msg=f"Found message with link", level=INFO)

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

    logger.log(msg=f"Matches: {len(matches)}", level=INFO)

    if len(matches) >= spam_threshold:
        for msg in matches:
            try:
                await msg.delete()
            except discord.Forbidden:
                pass
        try:
            await message.guild.ban(message.author, reason="Link spam in multiple channels")
            moderation_channel = bot.get_channel(WellKnown.channel_moderators)
            moderator_mention = moderation_channel.guild.get_role(WellKnown.role_moderator).mention
            await moderation_channel.send(f"{moderator_mention} Banned {message.author.mention} for spamming links")
        except discord.Forbidden:
            logger.log(msg=f"Couldn't ban {message.author} — missing permissions", level=INFO)
        link_message_cache.pop(user_id, None)
