from logging import getLogger
from os import environ

from discord import Bot, Cog

logger = getLogger(__name__)
is_dev = environ.get("ENV") == "dev"

class ProdCommands(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

def setup(bot: Bot):
    logger.info(f"Registering prod commands")
    bot.add_cog(ProdCommands(bot))