import aiohttp
import base64
import re
import os
from discord.ext import commands

REPO = "Ghetto05/GhettosModding"
BRANCH = "main"
BASE_URL = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}"
API_URL = f"https://api.github.com/repos/{REPO}"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def setup_changelog_update(bot: commands.Bot):
    @bot.event
    async def on_ready():
        print(f"🤖 Logged in as {bot.user}")
        bot.loop.create_task(start_webhook_server(bot))
        await run_changelog_update(bot)

    @bot.command(name="update")
    async def update_command(ctx):
        await ctx.send("🔄 Updating changelogs...")
        await run_changelog_update(bot)
        await ctx.send("✅ Done.")

async def run_changelog_update(bot):
    async with aiohttp.ClientSession() as session:
        channels = await get_mappings(session, "_Publish/ChangelogChannels.md")
        filenames = await get_mappings(session, "_Publish/FileNames.md")

        for mod, channel_id in channels.items():
            versions = await get_all_changelog_versions(session, mod)
            for version in versions:
                await process_changelog(session, bot, mod, version, int(channel_id), filenames.get(mod))

# Webhook listener
from aiohttp import web

async def start_webhook_server(bot):
    async def handle_webhook(request):
        print("🌐 Webhook received")
        await run_changelog_update(bot)
        return web.Response(text="✅ Changelog update triggered")

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
            for f in files if f["name"].startswith(f"{mod}_") and f["name"].endswith(".md") and "_MessageID" not in f["name"]
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
    header = f"# {display_name or mod} {version}" + ("" if tag_exists else " (WIP)")
    content = f"{header}\n\n{changelog}"

    msg_id_file = f"_Publish/Changelogs/{mod_slug}_MessageID.txt"
    msg_id_raw = await fetch_raw_file(session, msg_id_file)
    msg_id = int(msg_id_raw.strip()) if msg_id_raw and msg_id_raw.strip().isdigit() else None

    channel = client.get_channel(channel_id)
    if not channel:
        print(f"⚠️ Channel {channel_id} not found.")
        return

    try:
        if msg_id:
            msg = await channel.fetch_message(msg_id)
            await msg.edit(content=content)
            print(f"✅ Updated: {mod_slug}")
        else:
            msg = await channel.send(content)
            await write_message_id_file(session, mod_slug, msg.id)
            print(f"🆕 Posted: {mod_slug}")
    except Exception as e:
        print(f"❌ Error handling {mod_slug}: {e}")
