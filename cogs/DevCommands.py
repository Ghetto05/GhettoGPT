from itertools import count

import MessageUtils
from GitHubChangelogUpdate import (
    run_changelog_update,
    weekly_changelog_update,
    send_enqueued_changelog_update,
    enqueue_changelog_change,
)
from discord import Bot, slash_command
from discord.commands import option
from logging import getLogger
from os import environ

import discord.ext


logger = getLogger(__name__)
is_dev = environ.get("ENV") == "dev"


class DevCommands(discord.Cog):
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


    @slash_command(name="test-weekly-changelog", description="[Test] Sends a test message to the weekly changelog update channel", guild_ids=[954740284758032425])
    async def test_weekly_changelog(self, ctx: discord.ApplicationContext):
        if not is_dev:
            await ctx.respond("This is a test command and must not be used in production!")
            return
        await ctx.respond("Testing changelog update...")
        await weekly_changelog_update()
        await ctx.send_followup("Done.")


    @slash_command(name="simulate-changelog-addition", description="[Test] Simulates a single mod's changelog being updated", guild_ids=[954740284758032425])
    @option(
        "mod",
        description="The mod which should be enqueued for",
        input_type=str,
        required=True
    )
    @option(
        "changes",
        description="The changes that should be enqueued (separated by \\n)",
        input_type=str,
        required=True
    )
    async def simulate_changelog_addition(self, ctx: discord.ApplicationContext, mod: str, changes: str):
        if not is_dev:
            await ctx.respond("This is a test command and must not be used in production!")
            return
        await ctx.respond(f"Enqueuing changes to current changelog update for mod {mod}...")
        await enqueue_changelog_change(mod, "", changes.replace("\\n", "\n"))
        await ctx.send_followup("Done.")


    @slash_command(name="simulate-changelog-finished", description="[Test] Simulates the changelog update finishing", guild_ids=[954740284758032425])
    async def simulate_changelog_update_finished(self, ctx: discord.ApplicationContext):
        if not is_dev:
            await ctx.respond("This is a test command and must not be used in production!")
            return
        await ctx.respond("Sending changelog update...")
        await send_enqueued_changelog_update(self.bot)
        await ctx.send_followup("Done.")


    @slash_command(name="find-all-messages", description="[Test] Find all messages with any of the words given", guild_ids=[954740284758032425])
    @option(
        "words",
        description="The words that should be searched for",
        input_type=str,
        required=True
    )
    async def find_all_messages(self, ctx: discord.ApplicationContext, words: str):
        if not is_dev:
            await ctx.respond("This is a test command and must not be used in production!")
            return
        await ctx.respond("Searching for messages...")
        word_list = [w.strip() for w in words.split(",")]
        messages = await MessageUtils.find_messages_with_words(ctx.guild, word_list)

        message_texts = []
        current_length = 0
        remaining = 0
        checked = 0

        for msg in messages:
            msg_text = str(msg) + "\n"
            if current_length + len(msg_text) <= 1900:
                message_texts.append(msg_text)
                current_length += len(msg_text)
            else:
                remaining += 1
            checked += 1

        formatted_message = "".join(message_texts)
        if remaining > 0:
            formatted_message += f"\n(*{remaining}* more messages)"

        await ctx.message.channel.send(content=f"{ctx.author.mention} Found messages: {checked}\n\n{formatted_message}")


def setup(bot: Bot):
    logger.info(f"Registering dev commands")
    bot.add_cog(DevCommands(bot))