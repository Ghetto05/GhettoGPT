from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from discord import Bot
from flask import Flask, request
from logging import ERROR, INFO, getLogger
from packaging.version import parse as parse_version
from typing import Optional

import aiofiles
import aiofiles.os
import aiohttp
import asyncio
import base64
import difflib
import discord
import discord.ext
import logging
import os
import pathlib
import re
import threading
import WellKnown

TAG_REPO = "Ghetto05/Mods"
FILE_REPO = "Ghetto05/GhettosModding"
FILE_BRANCH = "master"
BASE_URL = f"https://raw.githubusercontent.com/{FILE_REPO}/refs/heads/{FILE_BRANCH}"
API_URL = "https://api.github.com/repos/{}"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
logger = getLogger(__name__)
app = Flask(__name__)
webhook_output_channel: Optional[discord.channel] = None
flask_started = False
webhook_bot: Optional[discord.Bot] = None
webhook_update_running = False
changelog_update_queue: dict[str, list[str]] = {}


def setup(bot: Bot):
    global webhook_bot
    webhook_bot = bot


#region Webhook setup


async def setup_changelog_update_webhook():
    global flask_started, webhook_output_channel, webhook_bot

    logger.info("Setting up changelog update webhook")

    webhook_output_channel = webhook_bot.get_channel(WellKnown.channel_bot_setup)

    if not flask_started:
        threading.Thread(target=run_flask, daemon=True).start()
        flask_started = True


def setup_changelog_summary_scheduler(scheduler: AsyncIOScheduler):
    scheduler.add_job(
        weekly_changelog_update,
        CronTrigger(day_of_week='fri', hour=12, minute=0, timezone='UTC')
    )


def run_flask():
    app.run(host="0.0.0.0", port=5000)


@app.route('/webhooks/discord-bot/changelog-update', methods=['POST'])
def changelog_webhook():
    logger.info("Changing log update webhook triggered")
    if webhook_output_channel:
        asyncio.run_coroutine_threadsafe(
            changelog_update(),
            webhook_bot.loop
        )
    return '', 204


#endregion


async def changelog_update():
    global webhook_update_running
    if webhook_update_running:
        logger.log(msg="Changelog update already running", level=ERROR)
        return
    webhook_update_running = True
    logger.info(f"Changelog update triggered by webhook")
    await run_changelog_update(webhook_bot, False)
    logger.info(f"Changelog update done")
    webhook_update_running = False


async def run_changelog_update(bot: discord.Bot, all_versions: bool):
    async with aiohttp.ClientSession() as session:
        channels = await get_mappings(session, "ChangelogChannels.md")

        for mod, channel_id in channels.items():
            versions = await get_all_changelog_versions(session, mod)

            versions.sort(key=lambda v: parse_version(v))

            target_versions = versions if all_versions else [versions[-1]]

            for version in target_versions:
                await process_changelog(session, bot, mod, version, int(channel_id))
                await asyncio.sleep(1)

        await send_enqueued_changelog_update(bot)


#region GitHub utils


async def fetch_raw_file(session, path) -> str:
    url = f"{BASE_URL}/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3.raw"}
    async with session.get(url, headers=headers) as resp:
        return await resp.text() if resp.status == 200 else None


async def fetch_json(session, url):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    async with session.get(url, headers=headers) as resp:
        return await resp.json() if resp.status == 200 else None


async def check_tag_exists(session, tag_name):
    url = f"{API_URL.format(TAG_REPO)}/git/ref/tags/{tag_name}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    async with session.get(url, headers=headers) as resp:
        return resp.status == 200


async def get_mappings(session, file_path):
    raw = await fetch_raw_file(session, file_path)
    mapping = {}
    if raw:
        for line in raw.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                mapping[k.strip()] = v.strip()
    return mapping


async def get_all_changelog_versions(session, mod):
    url = f"{API_URL.format(FILE_REPO)}/contents/Changelogs"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    async with session.get(url, headers=headers) as resp:
        if resp.status != 200:
            return []

        files = await resp.json()
        return [
            re.match(fr"{mod}_(.+)\.md", f["name"]).group(1)
            for f in files if
            f["name"].startswith(f"{mod}_") and f["name"].endswith(".md") and "_MessageID" not in f["name"]
        ]


#endregion


async def write_message_id_file(session, mod_slug, msg_id):
    path = f"Changelogs/MetaData/{mod_slug}_MessageID.txt"
    url = f"{API_URL.format(FILE_REPO)}/contents/{path}"
    content = str(msg_id).encode("utf-8")
    encoded = base64.b64encode(content).decode()

    async with session.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"}) as resp:
        sha = (await resp.json()).get("sha") if resp.status == 200 else None

    payload = {
        "message": f"Update MessageID for {mod_slug}",
        "content": encoded,
        "branch": FILE_BRANCH,
        **({"sha": sha} if sha else {})
    }

    async with session.put(url, headers={"Authorization": f"token {GITHUB_TOKEN}"}, json=payload) as resp:
        return resp.status in (200, 201)


async def process_changelog(session, bot: discord.Bot, mod, version, channel_id):
    mod_slug = f"{mod}_{version}"
    changelog = await fetch_raw_file(session, f"Changelogs/{mod_slug}.md")
    if not changelog:
        return

    tag_exists = await check_tag_exists(session, mod_slug)
    title = f"Release {version}" + ("" if tag_exists else " (WIP)")

    if len(changelog) > 4096:
        logger.log(msg=f"Changelog too long ({len(changelog)} chars) — must be ≤ 4096 for embed.", level=ERROR)
        return

    embed = discord.Embed(title=title, description=changelog, color=0xFF4F00)

    channel = bot.get_channel(channel_id)
    if not channel:
        logger.log(msg=f"Channel {channel_id} not found.", level=ERROR)
        return

    msg_id_file = f"Changelogs/MetaData/{mod_slug}_MessageID.txt"
    msg_id_raw = await fetch_raw_file(session, msg_id_file)
    msg_id = int(msg_id_raw.strip()) if msg_id_raw and msg_id_raw.strip().isdigit() else None

    try:
        if msg_id:
            original_msg = await channel.fetch_message(msg_id)
            original_changelog = original_msg.embeds[0].description
            await original_msg.edit(content=None, embed=embed)
            await enqueue_changelog_change(mod_slug, original_changelog, changelog.strip())
        else:
            msg = await channel.send(embed=embed)
            await write_message_id_file(session, mod_slug, msg.id)
            await enqueue_changelog_change(mod_slug, "", changelog.strip())

        logger.log(msg=f"Updated embed for {mod_slug} ({len(changelog.strip())} chars)", level=INFO)

    except Exception as e:
        logger.log(msg=f"Error posting embed for {mod_slug}: {e}", level=ERROR)


async def enqueue_changelog_change(mod_slug: str, old_content: str, new_content: str):
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()

    mod_name = mod_slug.split('_', 1)[0]

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    additions = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "insert" or tag == "replace":
            additions.extend(new_lines[j1:j2])

    if len(additions) == 0:
        return

    global changelog_update_queue
    changelog_update_queue[mod_slug] = additions

    await append_changelog_to_weekly_queue(mod_name, additions)


async def send_enqueued_changelog_update(bot: Bot):
    channel = bot.get_channel(WellKnown.get_channel(WellKnown.channel_changelog_update))
    mention = channel.guild.get_role(WellKnown.role_changelog_update).mention
    output = ""
    for key, values in changelog_update_queue.items():
        lines = "\n".join(values)
        output += f"\n\n## Update to {key}:\n{lines}" #ToDo: use proper mod name and version
    await channel.send(f"{mention}{output}")


async def append_changelog_to_weekly_queue(mod_name: str, additions: [str]): # take "ModName" part before first underscore
    queued_dir = pathlib.Path("Changelogs")
    queued_dir.mkdir(parents=True, exist_ok=True)
    queued_file = queued_dir / f"{mod_name}_QueuedWeeklyUpdate.md"

    # Prepare text to append (add heading if file does not exist yet)
    if not queued_file.exists():
        to_write = f"## {mod_name}\n" #ToDo: use actual mod name and version
    else:
        to_write = "\n"

    to_write += "\n".join(additions) + "\n"

    import aiofiles
    async with aiofiles.open(queued_file, mode="a", encoding="utf-8") as f:
        await f.write(to_write)


async def weekly_changelog_update():
    logger.log(msg="Sending weekly changelog summary", level=logging.INFO)
    channel = webhook_bot.get_channel(WellKnown.get_channel(WellKnown.channel_weekly_changelog_update))
    mention = channel.guild.get_role(WellKnown.role_weekly_changelog_update).mention
    changes = await fetch_summary()
    message = "### There were no changes this week."
    if changes != "None":
        message = f"### The following changes were added in the past week:\n\n{changes}\n-# **NOTE:**\n-# Changes that were previously added may have been removed.\n-# This summary only shows additions since the last week\n-# If you want to see all changes, please check the respective changelog channel."
    await channel.send(content=f"{mention}", embed=discord.Embed(description=message[:4096], color=0xFF4F00))


async def fetch_summary() -> str:
    import pathlib
    queued_dir = pathlib.Path("Changelogs")
    if not queued_dir.exists():
        return "None"
    output = ""
    files = list(queued_dir.glob("*_QueuedWeeklyUpdate.md"))
    if not files:
        return "None"

    for queued_file in files:
        # Read contents
        async with aiofiles.open(queued_file, mode="r", encoding="utf-8") as f:
            content = await f.read()
        output += content + "\n"

        # Delete file after reading
        await aiofiles.os.remove(queued_file)

    return output if output.strip() else "None"
