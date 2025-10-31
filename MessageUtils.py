from typing import List, Tuple
from discord import Guild
import re


async def find_messages_with_words(guild: Guild, words: List[str]) -> List[Tuple[int, str]]:
    matching_messages = []
    patterns = [re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE) for word in words]

    for channel in guild.text_channels:
        try:
            async for message in channel.history(limit=None):
                if any(pattern.search(message.content) for pattern in patterns):
                    matching_messages.append((message.id, message.content))
        except:
            continue

    return matching_messages
