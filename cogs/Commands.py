from logging import getLogger, INFO
import discord.ext
from discord import Bot, slash_command
from discord.commands import option
import ChangelogUpdateNotifier
from FakeIPGetter import generate_public_ipv4
from ChangelogUpdate import run_changelog_update
from GitHubBoardUpdate import update_github_board

logger = getLogger(__name__)


class Commands(discord.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command(name="update-changelog", description="Update the changelogs", guild_ids=[954740284758032425])
    @option(
        "all_versions",
        description="Update all changelogs",
        input_type=bool,
        required=True
    )
    async def update_changelogs(self, ctx: discord.ApplicationContext, all_versions: bool):
        await ctx.respond("Updating changelogs...")
        await run_changelog_update(self.bot, all_versions)
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

    @slash_command(name="update-github-board", description="Update the GitHub issue board", guild_ids=[954740284758032425])
    async def update_github_board(self, ctx: discord.ApplicationContext):
        await ctx.respond("Updating GitHub issues...")
        await update_github_board(self.bot)
        await ctx.respond("Done.")

    @slash_command(name="test-changelog-notification", description="Sends a test message to the changelog updat channels", guild_ids=[954740284758032425])
    async def test_changelog_update(self, ctx: discord.ApplicationContext):
        await ctx.respond("Testing changelog update...")
        await ChangelogUpdateNotifier.send_changelog_update(self.bot)
        await ChangelogUpdateNotifier.send_weekly_changelog_summary()
        await ctx.respond("Done.")


def setup(bot: Bot):
    logger.log(msg=f"Registering commands", level=INFO)
    bot.add_cog(Commands(bot))
