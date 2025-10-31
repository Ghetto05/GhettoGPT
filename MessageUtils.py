from logging import getLogger
from typing import List, Tuple
from discord import Guild
import re

logger = getLogger(__name__)

async def find_messages_with_words(guild: Guild, words: List[str]) -> List[Tuple[int, str]]:
    matching_messages = []
    patterns = [re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE) for word in words]

    logger.info(f"Searching for messages with words {words}")

    for channel in guild.text_channels:
        logger.info(f"Searching channel {channel.name}")
        try:
            history = channel.history(limit=None).flatten()
            logger.info(f"Checking {len(history)} messages...")
            checked = 0
            async for message in history:
                if any(pattern.search(message.content) for pattern in patterns):
                    matching_messages.append((message.id, message.content))
                checked += 1
                if checked % 1000 == 0:
                    logger.info(f"Checked {checked} messages...")
        except Exception as e:
            logger.error(f"Failed to search channel {channel.name}:\n\n{e}\n\n")

    return matching_messages
