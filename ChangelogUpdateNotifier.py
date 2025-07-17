import logging
import os
from collections import defaultdict
from datetime import timedelta
from logging import getLogger
from typing import Optional
import aiohttp
import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from discord import Bot
import WellKnown

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = "Ghetto05/GhettosModding"

logger = getLogger(__name__)
update_bot: Optional[Bot] = None


def setup_changelog_summary_scheduler(bot: Bot, scheduler: AsyncIOScheduler):
    global update_bot
    update_bot = bot
    scheduler.add_job(
        send_weekly_changelog_summary,
        CronTrigger(day_of_week='fri', hour=12, minute=0, timezone='UTC')
    )


async def send_weekly_changelog_summary():
    logger.log(msg="Sending weekly changelog summary", level=logging.INFO)
    channel = update_bot.get_channel(WellKnown.channel_weekly_changelog_update)
    mention = channel.guild.get_role(WellKnown.role_weekly_changelog_update).mention
    changes = await fetch_summary()
    message = "There were no changes this week."
    if changes != "None":
        message = "The following changes were added:\n\n" + changes
    await channel.send(content=f"{mention}", embed=discord.Embed(description=message[:4000], color=0xFF4F00))


async def send_changelog_update(bot: Bot):
    channel = bot.get_channel(WellKnown.channel_changelog_update)
    mention = channel.guild.get_role(WellKnown.role_changelog_update).mention
    await channel.send(f"{mention}\n")


async def fetch_summary() -> str:
    additions = await fetch_added_lines()
    if not additions:
        return "None"

    output = ""
    for file, lines in additions.items():
        file_title = file.split("/")[-1].replace(".md", "")
        output += f"## {file_title}\n"
        for line in lines:
            output += f"{line}\n"
        output += "\n"

    return output


async def fetch_added_lines():
    since = (discord.utils.utcnow() - timedelta(days=7)).isoformat() + "Z"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    base_url = f"https://api.github.com/repos/{REPO}"
    additions_by_file = defaultdict(list)

    async with aiohttp.ClientSession(headers=headers) as session:
        # 1. Get recent commits
        async with session.get(f"{base_url}/commits?since={since}") as resp:
            commits = await resp.json()

        for commit in commits:
            sha = commit["sha"]

            # 2. Get commit details
            async with session.get(f"{base_url}/commits/{sha}") as resp:
                commit_data = await resp.json()

            for file in commit_data.get("files", []):
                filename = file["filename"]

                if not (filename.startswith("Changelogs/") and filename.endswith(".md")):
                    continue

                patch = file.get("patch", "")
                if not patch:
                    continue

                # 3. Extract added lines
                for line in patch.splitlines():
                    if line.startswith("+") and not line.startswith("+++") and line.strip() != "+":
                        additions_by_file[filename].append(line[1:].strip())

    return additions_by_file
