import base64
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
        message = f"The following changes were added in the past week:\n\n{changes}\n-# **NOTE:**\n-# Changes that were previously added may have been removed.\n-# This summary only shows additions since the last week\n-# If you want to see all changes, please check the respective changelog channel."
    await channel.send(content=f"{mention}", embed=discord.Embed(description=message[:4096], color=0xFF4F00))


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
    since_dt = discord.utils.utcnow() - timedelta(hours=14)
    since_iso = since_dt.isoformat() + "Z"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    base_url = f"https://api.github.com/repos/{REPO}"
    additions_by_file = defaultdict(list)

    async with aiohttp.ClientSession(headers=headers) as session:
        # 1. List all files in Changelogs folder (via contents API)
        async with session.get(f"{base_url}/contents/Changelogs") as resp:
            changelog_files = await resp.json()

        for entry in changelog_files:
            if not entry["name"].endswith(".md"):
                continue

            filename = entry["path"]

            # 2. Get all commits for this file (to find history)
            async with session.get(f"{base_url}/commits?path={filename}&per_page=100") as resp:
                all_commits = await resp.json()

            if not all_commits:
                continue

            # 3. Check if file is new (created < 7 days ago)
            creation_commit = all_commits[-1]
            creation_date = creation_commit["commit"]["committer"]["date"]

            if creation_date > since_iso:
                # File is new — include entire content
                async with session.get(f"{base_url}/contents/{filename}") as resp:
                    file_data = await resp.json()
                content = base64.b64decode(file_data["content"]).decode("utf-8")
                lines = [line.strip() for line in content.splitlines() if line.strip()]
                additions_by_file[filename].extend(lines)
                continue

            # 4. Filter commits in the past 7 days
            recent_commits = [
                c for c in all_commits
                if c["commit"]["committer"]["date"] > since_iso
            ]
            if not recent_commits:
                continue  # no relevant changes

            # 5. Get latest version of the file
            async with session.get(f"{base_url}/contents/{filename}") as resp:
                latest_data = await resp.json()
            latest_content = base64.b64decode(latest_data["content"]).decode("utf-8")
            latest_lines = [line.strip() for line in latest_content.splitlines() if line.strip()]

            # 6. Get content from the most recent commit before or equal to 7 days ago
            base_commit = None
            for commit in reversed(all_commits):
                if commit["commit"]["committer"]["date"] <= since_iso:
                    base_commit = commit
                    break

            if not base_commit:
                continue  # fail-safe

            base_sha = base_commit["sha"]
            async with session.get(f"{base_url}/contents/{filename}?ref={base_sha}") as resp:
                base_data = await resp.json()
            base_content = base64.b64decode(base_data["content"]).decode("utf-8")
            base_lines = [line.strip() for line in base_content.splitlines() if line.strip()]

            # 7. Compare lines and collect only additions
            diff = difflib.ndiff(base_lines, latest_lines)
            added = [line[2:].strip() for line in diff if line.startswith("+ ")]

            if added:
                additions_by_file[filename].extend(added)

    return additions_by_file
