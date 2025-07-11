import logging

import discord.ext
from discord import Bot, slash_command
from discord.commands import option

from FakeIPGetter import generate_public_ipv4
from ChangelogUpdate import run_changelog_update

logger = logging.getLogger(__name__)


class Commands(discord.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command(name="update", description="Update the changelogs", guild_ids=[954740284758032425])
    async def setup_commands(self, ctx: discord.ApplicationContext):
        await ctx.respond("Updating changelogs...")
        await run_changelog_update(self.bot)
        await ctx.respond("Done.")

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
    logger.log(msg=f"Registering commands", level=logging.INFO)
    bot.add_cog(Commands(bot))
