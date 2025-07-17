import asyncio
import logging
from datetime import timedelta
from logging import getLogger
from typing import Optional

import aiohttp
import os
from collections import defaultdict
import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from discord import Bot

import WellKnown

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
logger = getLogger(__name__)
update_bot: Optional[Bot] = None
update_interval_minutes = 10


def setup_github_board_update(bot: Bot, scheduler: AsyncIOScheduler):
    global update_bot
    update_bot = bot
    # Round to next hour
    next_hour = get_next_interval()

    # Schedule first run at the top of the next hour
    scheduler.add_job(
        run_periodic_update,
        trigger=DateTrigger(run_date=next_hour)
    )
    logger.log(msg=f"Next GitHub Board update scheduled for {next_hour}", level=logging.INFO)

    # Schedule recurring run every hour after that
    scheduler.add_job(
        run_periodic_update,
        trigger=IntervalTrigger(minutes=update_interval_minutes, start_date=next_hour)
    )
    logger.log(msg=f"GitHub Board update scheduled to run every {update_interval_minutes} starting at {next_hour}", level=logging.INFO)


async def run_periodic_update():
    while True:
        try:
            logger.log(msg="Updating GitHub Board", level=logging.INFO)
            await update_github_board(update_bot)
        except Exception as e:
            logger.log(msg="Error in updating GitHub board: {e}", level=logging.ERROR)
        await asyncio.sleep(60 * 60)


def get_next_interval():
    now = discord.utils.utcnow().replace(second=0, microsecond=0)
    minute = (now.minute // update_interval_minutes + 1) * update_interval_minutes
    next_run = now.replace(minute=0) + timedelta(minutes=minute)

    if next_run.minute >= 60:
        next_run = next_run.replace(minute=0) + timedelta(hours=1)

    return next_run


async def update_github_board(bot: Bot):
    status_issue_groups = await fetch_project_issues()
    now = discord.utils.utcnow()
    next_run = now.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=update_interval_minutes)
    message_content = f"# GitHub Issue Board\nLast update: <t:{int(now.timestamp())}:f>\nNext update: <t:{int(next_run.timestamp())}:R>\n"
    for status, issues in status_issue_groups.items():
        if status not in [ "Backlog", "Urgent ToDo", "In progress", "Testing", ]:
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
    query($after: String) {
      user(login: "Ghetto05") {
        projectV2(number: 3) {
          items(first: 100, after: $after) {
            pageInfo {
              hasNextPage
              endCursor
            }
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

    issues_by_status = defaultdict(list)
    has_next_page = True
    after = None

    async with aiohttp.ClientSession() as session:
        while has_next_page:
            variables = {"after": after}
            async with session.post(url, json={"query": query, "variables": variables}, headers=headers) as resp:
                data = await resp.json()

                try:
                    items_data = data["data"]["user"]["projectV2"]["items"]
                except KeyError:
                    logging.error(f"GitHub API error: {data}")
                    break

                for item in items_data["nodes"]:
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

                has_next_page = items_data["pageInfo"]["hasNextPage"]
                after = items_data["pageInfo"]["endCursor"]

    return issues_by_status
