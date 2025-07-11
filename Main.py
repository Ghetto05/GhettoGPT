import logging
import os
import discord
from discord.ext import commands
import WellKnown
from ChangelogUpdate import setup_changelog_update_webhook
from SpamBanner import check_and_ban_link_spammer

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

initialized = False

intents = discord.Intents.all()
intents.members = True
intents.message_content = True
intents.presences = True

bot = commands.Bot(intents=intents)
logger = logging.getLogger(__name__)

extensions = ("cogs.Commands",)

for extension in extensions:
    bot.load_extension(extension)


@bot.event
async def on_ready():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.log(msg=f"Logged in as {bot.user}", level=logging.INFO)

    # start up message
    global initialized
    if not initialized:
        initialized = True
        await bot.get_channel(WellKnown.channel_bot_setup).send(f"{bot.get_user(WellKnown.user_ghetto05).mention} Starting up...")

    await setup_changelog_update_webhook(bot)


@bot.event
async def on_message(message: discord.Message):
    logger.log(msg=f"Message received: {message.content}", level=logging.INFO)
    if message.author.bot:
        return

    await check_and_ban_link_spammer(message, bot)

    if bot.user in message.mentions:
        await message.channel.send(f"Hi {message.author.display_name}!")

    await bot.process_commands(message)


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logger.log(msg="DISCORD_TOKEN is missing.", level=logging.ERROR)
        exit(1)
    bot.run(DISCORD_TOKEN)
