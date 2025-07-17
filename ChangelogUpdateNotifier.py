import difflib
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


async def send_changelog_update_notification(bot: Bot, file: str, old_content: str, new_content: str):
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    additions = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "insert" or tag == "replace":
            additions.extend(new_lines[j1:j2])

    if len(additions) == 0:
        return

    channel = bot.get_channel(WellKnown.channel_changelog_update)
    mention = channel.guild.get_role(WellKnown.role_changelog_update).mention
    await channel.send(f"{mention}\nUpdate to\n**{file}**\n" + "\n".join(additions))


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
        message = "The following changes were added in the past week:\n\n" + changes
    await channel.send(content=f"{mention}", embed=discord.Embed(description=message[:4000], color=0xFF4F00))


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
    since = (discord.utils.utcnow() - timedelta(hours=14)).isoformat() + "Z"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    base_url = f"https://api.github.com/repos/{REPO}"
    additions_by_file = defaultdict(list)

    async with aiohttp.ClientSession(headers=headers) as session:
        # 1. Get list of files in Changelogs/
        async with session.get(f"{base_url}/contents/Changelogs") as resp:
            changelog_files = await resp.json()

        for file in changelog_files:
            filename = file["path"]
            if not filename.endswith(".md"):
                continue

            # 2. Fetch current content
            async with session.get(file["download_url"]) as resp:
                current_text = await resp.text()
            current_lines = set(l.strip() for l in current_text.splitlines() if l.strip())

            # 3. Get commit from >= 7 days ago that modified this file
            async with session.get(f"{base_url}/commits?path={filename}&until={since}") as resp:
                old_commits = await resp.json()

            if not old_commits:
                # File was added within 7 days, keep all lines
                additions_by_file[filename] = list(current_lines)
                continue

            # 4. Fetch old version of the file
            old_sha = old_commits[0]["sha"]
            async with session.get(f"{base_url}/contents/{filename}?ref={old_sha}") as resp:
                old_file_data = await resp.json()
                import base64
                old_text = base64.b64decode(old_file_data["content"]).decode("utf-8")
            old_lines = set(l.strip() for l in old_text.splitlines() if l.strip())

            # 5. Diff: only lines that are new
            new_lines = [line for line in current_text.splitlines()
                         if line.strip() and line.strip() not in old_lines]

            if new_lines:
                additions_by_file[filename] = new_lines

    return additions_by_file
