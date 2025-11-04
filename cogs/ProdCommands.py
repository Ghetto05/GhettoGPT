from logging import getLogger
from os import environ
from discord import ApplicationContext, Bot, Cog, slash_command

import DevOpsBoardUpdate
import GitHubBoardUpdate

logger = getLogger(__name__)
is_dev = environ.get("ENV") == "dev"

class ProdCommands(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command(name="update-github-board", description="Update the GitHub issue board",
                   guild_ids=[954740284758032425])
    async def update_github_board(self, ctx: ApplicationContext):
        await ctx.respond("Updating GitHub issues...")
        await GitHubBoardUpdate.update_board(self.bot)
        await ctx.send_followup("Done.")

    @slash_command(name="update-devops-board", description="Update the DevOps issue board",
                   guild_ids=[954740284758032425])
    async def update_devops_board(self, ctx: ApplicationContext):
        await ctx.respond("Updating DevOps issues...")
        await DevOpsBoardUpdate.update_board(self.bot)
        await ctx.send_followup("Done.")

def setup(bot: Bot):
    logger.info(f"Registering prod commands")
    bot.add_cog(ProdCommands(bot))