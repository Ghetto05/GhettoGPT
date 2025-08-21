from ChangelogUpdate import (
    append_changelog_to_weekly_queue,
    fetch_summary,
    run_changelog_update,
    weekly_changelog_update,
)
from FakeIPGetter import generate_public_ipv4
from GitHubBoardUpdate import update_github_board
from discord import Bot, slash_command
from discord.commands import option
from logging import INFO, getLogger
from os import environ

import discord.ext

logger = getLogger(__name__)
is_dev = environ.get("ENV") == "dev"


class Commands(discord.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot


    @slash_command(name="update-changelog", description="[Test] Update the changelogs", guild_ids=[954740284758032425])
    @option(
        "all_versions",
        description="Update all changelogs",
        input_type=bool,
        required=True
    )
    async def update_changelogs(self, ctx: discord.ApplicationContext, all_versions: bool):
        if not is_dev:
            await ctx.respond("This is a test command and must not be used in production!")
            return
        await ctx.respond("Updating changelogs...")
        await run_changelog_update(self.bot, all_versions)
        await ctx.send_followup("Done.")


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
        await ctx.send_followup("Done.")


    @slash_command(name="test-weekly-changelog", description="[Test] Sends a test message to the weekly changelog update channel", guild_ids=[954740284758032425])
    async def test_weekly_changelog(self, ctx: discord.ApplicationContext):
        if not is_dev:
            await ctx.respond("This is a test command and must not be used in production!")
            return
        await ctx.respond("Testing changelog update...")
        await weekly_changelog_update()
        await ctx.send_followup("Done.")


    @slash_command(name="clear-weekly-changelog", description="[Test] Clears the weekly changelog update queue", guild_ids=[954740284758032425])
    async def clear_weekly_changelog(self, ctx: discord.ApplicationContext):
        if not is_dev:
            await ctx.respond("This is a test command and must not be used in production!")
            return
        await ctx.respond("Clearing weekly changelog cache...")
        await fetch_summary()
        await ctx.send_followup("Done.")


    @slash_command(name="append-weekly-changelog", description="[Test] Appends content to the weekly changelog update queue", guild_ids=[954740284758032425])
    @option(
        "mod",
        description="The mod which should be appended to",
        input_type=str,
        required=True
    )
    @option(
        "changes",
        description="The changes that should be appended (separated by |)",
        input_type=str,
        required=True
    )
    async def append_weekly_changelog(self, ctx: discord.ApplicationContext, mod: str, changes: str):
        if not is_dev:
            await ctx.respond("This is a test command and must not be used in production!")
            return
        change_collection = changes.split("|")
        await ctx.respond(f"Appending {len(change_collection)} changes to weekly changelog cache of mod {mod}...")
        await append_changelog_to_weekly_queue(mod, change_collection)
        await ctx.send_followup("Done.")


def setup(bot: Bot):
    logger.log(msg=f"Registering commands", level=INFO)
    bot.add_cog(Commands(bot))
