from logging import getLogger
from typing import List, Tuple
from discord import Guild
import re

logger = getLogger(__name__)

async def find_messages_with_words(guild: Guild, words: List[str]) -> List[Tuple[int, str]]:
    matching_messages = []
    patterns = [re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE) for word in words]

    channels = [
        #954741258545418270, # general
        1052938720514420797, # non-english
        #1285384126542774384, # qna
        1200949055325491262, # quote-pit
        1018586521210724392, # screenshots
        1080825809125769288, # gun-creation-discussion
        #974281568388546611, # memes
        #1030587137797664858, # media
        #1196069832022573136, # clips
        #1113283690240417812, # cursed-firearms
        #1194049277710831666 # schizo-posting
    ]

    logger.info(f"Searching for messages with words {words}")

    for channel in guild.text_channels:
        if channel.id not in channels:
            continue
        logger.info(f"Searching channel {channel.name}")
        try:
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
