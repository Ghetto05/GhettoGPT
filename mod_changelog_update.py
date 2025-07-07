import logging
import aiohttp
import discord
from aiohttp import web
import base64
import re
import os

REPO = "Ghetto05/Mods"
BRANCH = "main"
BASE_URL = f"https://raw.githubusercontent.com/{REPO}/refs/heads/{BRANCH}"
API_URL = f"https://api.github.com/repos/{REPO}"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

logger = logging.getLogger(__name__)


async def run_changelog_update(bot: discord.ext.commands.Bot):
    async with aiohttp.ClientSession() as session:
        channels = await get_mappings(session, "_Publish/ChangelogChannels.md")
        filenames = await get_mappings(session, "_Publish/FileNames.md")

        for mod, channel_id in channels.items():
            versions = await get_all_changelog_versions(session, mod)
            logger.log(logging.INFO, f"Found {len(versions)} versions for {mod}")
            for version in versions:
                await process_changelog(session, bot, mod, version, int(channel_id), filenames.get(mod))


async def start_webhook_server(bot: discord.ext.commands.Bot):
    async def handle_webhook(request):
        logger.log(msg="Webhook received", level=logging.INFO)
        await run_changelog_update(bot)
        return web.Response(text="Changelog update triggered")

    app = web.Application()
    app.router.add_post("/webhooks/ghettogpt/update_changelog", handle_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()


async def fetch_raw_file(session, path):
    url = f"{BASE_URL}/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3.raw"}
    async with session.get(url, headers=headers) as resp:
        return await resp.text() if resp.status == 200 else None


async def fetch_json(session, url):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    async with session.get(url, headers=headers) as resp:
        return await resp.json() if resp.status == 200 else None


async def check_tag_exists(session, tag_name):
    url = f"{API_URL}/git/ref/tags/{tag_name}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    async with session.get(url, headers=headers) as resp:
        return resp.status == 200


async def write_message_id_file(session, mod_slug, msg_id):
    path = f"_Publish/Changelogs/{mod_slug}_MessageID.txt"
    url = f"{API_URL}/contents/{path}"
    content = str(msg_id).encode("utf-8")
    encoded = base64.b64encode(content).decode()

    async with session.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"}) as resp:
        sha = (await resp.json()).get("sha") if resp.status == 200 else None

    payload = {
        "message": f"Update MessageID for {mod_slug}",
        "content": encoded,
        "branch": BRANCH,
        **({"sha": sha} if sha else {})
    }

    async with session.put(url, headers={"Authorization": f"token {GITHUB_TOKEN}"}, json=payload) as resp:
        return resp.status in (200, 201)


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
    url = f"{API_URL}/contents/_Publish/Changelogs"
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


async def process_all_changelogs(client):
    async with aiohttp.ClientSession() as session:
        channels = await get_mappings(session, "_Publish/ChangelogChannels.md")
        filenames = await get_mappings(session, "_Publish/FileNames.md")

        for mod, channel_id in channels.items():
            versions = await get_all_changelog_versions(session, mod)
            for version in versions:
                await process_changelog(session, client, mod, version, int(channel_id), filenames.get(mod))


async def process_changelog(session, client, mod, version, channel_id, display_name):
    mod_slug = f"{mod}_{version}"
    changelog = await fetch_raw_file(session, f"_Publish/Changelogs/{mod_slug}.md")
    if not changelog:
        return

    tag_exists = await check_tag_exists(session, mod_slug)
    title = f"Release {version}" + ("" if tag_exists else " (WIP)")

    if len(changelog) > 4096:
        logger.log(msg=f"Changelog too long ({len(changelog)} chars) — must be ≤ 4096 for embed.", level=logging.ERROR)
        return

    embed = discord.Embed(title=title, description=changelog, color=0xFF4F00)

    channel = client.get_channel(channel_id)
    if not channel:
        logger.log(msg=f"Channel {channel_id} not found.", level=logging.ERROR)
        return

    msg_id_file = f"_Publish/Changelogs/{mod_slug}_MessageID.txt"
    msg_id_raw = await fetch_raw_file(session, msg_id_file)
    msg_id = int(msg_id_raw.strip()) if msg_id_raw and msg_id_raw.strip().isdigit() else None

    try:
        if msg_id:
            original_msg = await channel.fetch_message(msg_id)
            await original_msg.edit(content=None, embed=embed)
        else:
            msg = await channel.send(embed=embed)
            await write_message_id_file(session, mod_slug, msg.id)

        logger.log(msg=f"Updated embed for {mod_slug} ({len(changelog)} chars)", level=logging.INFO)

    except Exception as e:
        logger.log(msg=f"Error posting embed for {mod_slug}: {e}", level=logging.ERROR)
