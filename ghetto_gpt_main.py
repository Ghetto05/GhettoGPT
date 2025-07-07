import logging
import os
import discord
from discord.ext import commands
from commands import setup_commands

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="/", intents=intents)
logger = logging.getLogger(__name__)

@bot.event
async def on_ready():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.log(msg=f"🤖 Logged in as {bot.user}", level=logging.INFO)
    if not hasattr(bot, "commands_registered"):
        setup_commands(bot)
        await bot.tree.sync()
        await bot.tree.sync(guild=discord.Object(id=954740284758032425))
        bot.commands_registered = True

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user in message.mentions:
        await message.channel.send(f"Hi {message.author.name}!")

    await bot.process_commands(message)

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logger.log(msg="❌ DISCORD_TOKEN is missing.", level=logging.ERROR)
        exit(1)
    bot.run(DISCORD_TOKEN)
