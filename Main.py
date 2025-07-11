import logging
import os
import discord
from discord.ext import commands

import FakeIPGetter
import WellKnownChannels
import ChangelogUpdate

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
intents.members = True
intents.message_content = True
intents.presences = True

bot = commands.Bot(intents=intents)
logger = logging.getLogger(__name__)

extensions = ("cogs.Commands",)

for extension in extensions:
    bot.load_extension(extension)

bot.get_channel(WellKnownChannels.BotSetup).send("Starting up...")


@bot.event
async def on_ready():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.log(msg=f"Logged in as {bot.user}", level=logging.INFO)
    await mod_changelog_update.setup_webhook(bot)


@bot.event
async def on_message(message: discord.Message):
    logger.log(msg=f"Message received: {message.content}", level=logging.INFO)
    if message.author.bot:
        return

    if bot.user in message.mentions:
        await message.channel.send(f"Hi {message.author.display_name}!")

    await bot.process_commands(message)


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logger.log(msg="DISCORD_TOKEN is missing.", level=logging.ERROR)
        exit(1)
    bot.run(DISCORD_TOKEN)
