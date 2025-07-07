import logging
import os
import discord
from discord.ext import commands
from commands import setup_commands
import mod_changelog_update

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
intents.members = True
intents.message_content = True
intents.presences = True

bot = commands.Bot()
logger = logging.getLogger(__name__)


@bot.event
async def on_ready():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.log(msg=f"Logged in as {bot.user}", level=logging.INFO)
    if not hasattr(bot, "commands_registered"):
        logger.log(msg=f"Registering commands", level=logging.INFO)
        setup_commands(bot)
        bot.commands_registered = True


@bot.event
async def on_message(message: discord.Message):
    logger.log(msg=f"Message received: {message.content}", level=logging.INFO)
    if message.author == bot.user:
        return

    if bot.user in message.mentions:
        await message.channel.send(f"Hi {message.author.name}!")

    if message.content == "/updatechangelog":
        await mod_changelog_update.process_all_changelogs()

    await bot.process_commands(message)


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logger.log(msg="DISCORD_TOKEN is missing.", level=logging.ERROR)
        exit(1)
    bot.run(DISCORD_TOKEN)
