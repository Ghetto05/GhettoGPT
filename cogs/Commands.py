from FakeIPGetter import generate_public_ipv4
from discord import Bot, slash_command
from discord.commands import option
from logging import getLogger
from os import environ

import DevOpsBoardUpdate
import GitHubBoardUpdate
import discord.ext

logger = getLogger(__name__)
is_dev = environ.get("ENV") == "dev"


class Commands(discord.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot


    @slash_command(name="grabip", description="Grab the IP of a specific user", guild_ids=[954740284758032425])
    @option(
        "user",
        description="The user to grab the IP of",
        input_type=discord.User,
        required=True
    )
    async def grab_ip(self, ctx: discord.ApplicationContext, user: discord.User):
        await ctx.respond(f"\"{user.display_name}\"'s IP is {generate_public_ipv4(user.id)}")


def setup(bot: Bot):
    logger.info(f"Registering commands")
    bot.add_cog(Commands(bot))
