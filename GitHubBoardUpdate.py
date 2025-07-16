import asyncio
import logging
from logging import getLogger
import aiohttp
import os
from collections import defaultdict
import discord
from discord import Bot

import WellKnown

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
logger = getLogger(__name__)


async def setup_github_board_update(bot: Bot):
    bot.loop.create_task(run_periodic_update(bot))


async def run_periodic_update(bot: Bot):
    while True:
        try:
            logger.log(msg="Updating GitHub Board", level=logging.INFO)
            await update_github_board(bot)
        except Exception as e:
            logger.log(msg="Error in updating GitHub board: {e}", level=logging.ERROR)
        await asyncio.sleep(60 * 60)


async def update_github_board(bot: Bot):
    status_issue_groups = await fetch_project_issues()
    message_content = f"# GitHub Issue Board\nLast update: <t:{int(discord.utils.utcnow().timestamp())}:f>\n"
    for status, issues in status_issue_groups.items():
        if status not in [ "Backlog", "ToDo", "Testing", ]:
            continue
        message_content += f"\n## {status}\n"
        for issue in issues:
            message_content += f"- #{issue['number']}: {issue['title']}\n"
    embed = discord.Embed(description=message_content, color=0xFF4F00)
    message = await bot.get_channel(WellKnown.channel_github_board).fetch_message(WellKnown.message_github_board)
    await message.edit(content="", embed=embed)


async def fetch_project_issues():
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }

    query = """
    query {
      user(login: "Ghetto05") {
        projectV2(number: 3) {
          items(first: 100) {
            nodes {
              content {
                ... on Issue {
                  title
                  number
                }
              }
              fieldValues(first: 10) {
                nodes {
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={'query': query}, headers=headers) as resp:
            data = await resp.json()

            issues_by_status = defaultdict(list)

            items = data["data"]["user"]["projectV2"]["items"]["nodes"]
            for item in items:
                content = item.get("content")
                if not content:
                    continue

                title = content["title"]
                number = content["number"]

                status = "Unknown"
                for field in item["fieldValues"]["nodes"]:
                    if "name" in field:
                        status = field["name"]
                        break

                issues_by_status[status].append({
                    "title": title,
                    "number": number,
                })

            return issues_by_status
