import random
from io import BytesIO
from logging import getLogger, INFO
from aiohttp import ClientSession
import discord.ext
from discord import Bot, slash_command

GITHUB_USER = "Ghetto05"
REPO = "RandomPrebuilts"
BRANCH = "main"

GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_USER}/{REPO}/contents?ref={BRANCH}"
RAW_BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO}/{BRANCH}"

logger = getLogger(__name__)


class RandomPrebuilt(discord.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command(name="randomgun", description="Get a random firearm save", guild_ids=[954740284758032425])
    async def setup_commands(self, ctx: discord.ApplicationContext):
        async with ClientSession() as session:
            # Step 1: Get list of folders from GitHub
            async with session.get(GITHUB_API_URL) as resp:
                if resp.status != 200:
                    return await ctx.send("Failed to fetch mod list from GitHub.")
                data = await resp.json()

            folders = [item["name"] for item in data if item["type"] == "dir"]
            if not folders:
                return await ctx.send("No mod folders found.")

            # Step 2: Pick one randomly
            folder = random.choice(folders)
            base_raw = f"{RAW_BASE_URL}/{folder}"

            txt_url = f"{base_raw}/title.txt"
            img_url = f"{base_raw}/image.png"
            json_url = f"{base_raw}/save.json"

            # Step 3: Fetch text and JSON file
            async with session.get(txt_url) as txt_resp:
                if txt_resp.status != 200:
                    return await ctx.send(f"Failed to load title.txt for `{folder}`.")
                title = (await txt_resp.text()).strip()

            async with session.get(json_url) as json_resp:
                if json_resp.status != 200:
                    return await ctx.send(f"Failed to load save.json for `{folder}`.")
                json_data = await json_resp.read()

        # Step 4: Send embed + attachment
        embed = discord.Embed(title=title, description=f"Mod: `{folder}`", color=0xFF4F00)
        embed.set_image(url=img_url)

        file = discord.File(BytesIO(json_data), filename=f"{folder}.json")
        await ctx.send(embed=embed, file=file)


def setup(bot: Bot):
    bot.add_cog(RandomPrebuilt(bot))
