import logging

import discord.ext
from discord import Bot, slash_command
from mod_changelog_update import run_changelog_update, start_webhook_server

logger = logging.getLogger(__name__)


class Commands(discord.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        bot.loop.create_task(start_webhook_server(bot))

    @slash_command(name="update", description="Update the changelogs", guild_ids=[954740284758032425])
    async def setup_commands(self, ctx: discord.ApplicationContext):
        await ctx.respond("Updating changelogs...")
        await run_changelog_update(self.bot)
        await ctx.respond("Done.")


def setup(bot: Bot):
    logger.log(msg=f"Registering commands", level=logging.INFO)
    bot.add_cog(Commands(bot))
