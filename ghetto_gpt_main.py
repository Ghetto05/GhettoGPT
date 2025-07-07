import os
import discord
from discord.ext import commands

from mod_changelog_update import setup_changelog_update

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)
setup_changelog_update(bot)

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN is missing.")
        exit(1)
    bot.run(DISCORD_TOKEN)
