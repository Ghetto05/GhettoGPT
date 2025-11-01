from logging import getLogger
from typing import List, Tuple
from discord import Guild
import re

logger = getLogger(__name__)

async def find_messages_with_words(guild: Guild, words: List[str]) -> List[Tuple[int, str]]:
    matching_messages = []
    patterns = [re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE) for word in words]

    channels = [
        954741258545418270,
        1052938720514420797,
        1285384126542774384,
        1200949055325491262,
        1369560585473359883,
        1373115021302960129,
        1374797823035572265,
        1018586521210724392,
        1080825809125769288,
        974281568388546611,
        1030587137797664858,
        1196069832022573136,
        1113283690240417812,
        1194049277710831666
    ]

    logger.info(f"Searching for messages with words {words}")

    for channel in guild.text_channels:
        if channel.id not in channels:
            continue
        logger.info(f"Searching channel {channel.name}")
        try:
            # logger.info(f"Checking {len(history)} messages...")
            checked = 0
            async for message in channel.history(limit=None):
                if any(pattern.search(message.content) for pattern in patterns):
                    matching_messages.append((message.id, message.content))
                checked += 1
                if checked % 1000 == 0:
                    logger.info(f"Checked {checked} messages...")
        except Exception as e:
            logger.error(f"Failed to search channel {channel.name}:\n{e}")

    return matching_messages
