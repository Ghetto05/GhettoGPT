from logging import getLogger
import aiohttp
import os
from collections import defaultdict
import discord
from discord import Bot

import WellKnown

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
logger = getLogger(__name__)


async def update_github_board(bot: Bot):
    status_issue_groups = await fetch_project_issues()
    message_content = f"# GitHub Issue Board\nLast update: <t:{int(discord.utils.utcnow().timestamp())}:f>\n"
    for status, issues in status_issue_groups.items():
        message_content += f"\n## {status}"
        for issue in issues:
            message_content += f"- #{issue['number']}: {issue['title']} (Last activity: {issue['last_activity']})\n"
    await bot.get_channel(WellKnown.channel_github_board).fetch_message(WellKnown.message_github_board).edit(content=message_content)


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
                  updatedAt
                  comments(last: 1) {
                    nodes {
                      updatedAt
                    }
                  }
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
                updated_at = content["updatedAt"]
                comments = content.get("comments", {}).get("nodes", [])
                last_comment = comments[0]["updatedAt"] if comments else updated_at

                status = "Unknown"
                for field in item["fieldValues"]["nodes"]:
                    if "name" in field:
                        status = field["name"]
                        break

                issues_by_status[status].append({
                    "title": title,
                    "number": number,
                    "last_activity": last_comment,
                })

            return issues_by_status
