from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord import Intents, Message
from discord.ext import commands
from SpamBanner import check_and_ban_link_spammer
from Webhooks import setup_webhooks

import GitHubBoardUpdate
import GitHubChangelogUpdate
import logging
import os
import WellKnown


intents = Intents.all()
intents.members = True
intents.message_content = True
intents.presences = True


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
initialized = False
bot = commands.Bot(intents=intents)
logger = logging.getLogger(__name__)
is_dev = os.environ.get("ENV") == "dev"
extensions = ("cogs.Commands", "cogs.RandomPrebuilt",)


for extension in extensions:
    bot.load_extension(extension)


if is_dev:
    bot.load_extension("cogs.DevCommands")
else:
    bot.load_extension("cogs.ProdCommands")


@bot.event
async def on_ready():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info(f"Logged in as {bot.user}")

    global initialized
    if not initialized:
        initialized = True
        GitHubChangelogUpdate.setup(bot)
        await setup_webhooks(bot)
        if not is_dev:
            scheduler = AsyncIOScheduler()
            scheduler.start()
            GitHubChangelogUpdate.setup_changelog_summary_scheduler(scheduler)
            GitHubBoardUpdate.setup_github_board_update(bot, scheduler)
        await (bot.get_channel(WellKnown.get_channel(WellKnown.channel_bot_setup)).send(
            f"{bot.get_user(WellKnown.user_ghetto05).mention} Starting up...{' (test instance - changelog rework)' if is_dev else ''}"))


@bot.event
async def on_message(message: Message):
    logger.info(f"Message received ({message.author.display_name}): {message.content}")
    if message.author.bot:
        return

    if not is_dev:
        await check_and_ban_link_spammer(message, bot)

    await bot.process_commands(message)

    if bot.user in message.mentions and message.author.id == WellKnown.user_ghetto05 and "send a message here please" in message.content:
        await message.channel.send("This is a message")


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN is missing.")
        exit(1)
    bot.run(DISCORD_TOKEN)
