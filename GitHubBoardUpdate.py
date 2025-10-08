from datetime import timedelta
from logging import getLogger, error
from os import getenv
from typing import Optional
from collections import defaultdict
from aiohttp import ClientSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from discord import Bot, Embed, utils

import WellKnown

GITHUB_TOKEN = getenv("GITHUB_TOKEN")
logger = getLogger(__name__)
update_bot: Optional[Bot] = None
update_interval_minutes = 10


def setup_board_update(bot: Bot, scheduler: AsyncIOScheduler):
    global update_bot
    update_bot = bot
    # Round to next hour
    next_hour = get_next_interval()

    # Schedule recurring run every update_interval_minutes minutes after next fitting interval
    scheduler.add_job(
        run_periodic_update,
        trigger=IntervalTrigger(minutes=update_interval_minutes, start_date=next_hour)
    )
    logger.info(f"GitHub Board update scheduled to run every {update_interval_minutes} minutes starting at {next_hour} UTC")


async def run_periodic_update():
    try:
        logger.info("Updating GitHub Board")
        await update_board(update_bot)
    except Exception:
        logger.error("Error in updating GitHub board: {e}")


def get_next_interval():
    now = utils.utcnow().replace(second=0, microsecond=0)
    minute = (now.minute // update_interval_minutes + 1) * update_interval_minutes
    next_run = now.replace(minute=0) + timedelta(minutes=minute)

    if next_run.minute >= 60:
        next_run = next_run.replace(minute=0) + timedelta(hours=1)

    return next_run


async def update_board(bot: Bot):
    status_issue_groups = await fetch_project_issues()
    now = utils.utcnow()
    next_run = get_next_interval()
    message_content = f"# GitHub Issue Board\nLast update: <t:{int(now.timestamp())}:f>\nNext update: <t:{int(next_run.timestamp())}:R>\n"
    for status, issues in status_issue_groups.items():
        if status not in [ "Backlog", "Urgent ToDo", "In progress", "Testing", ]:
            continue
        message_content += f"\n## {status}\n"
        for issue in issues:
            message_content += f"- #{issue['number']}: {issue['title']}\n"
    embed = Embed(description=message_content, color=0xFF4F00)
    message = await bot.get_channel(WellKnown.channel_issue_board).fetch_message(WellKnown.message_issue_board)
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

    async with ClientSession() as session:
        while has_next_page:
            variables = {"after": after}
            async with session.post(url, json={"query": query, "variables": variables}, headers=headers) as resp:
                data = await resp.json()

                try:
                    items_data = data["data"]["user"]["projectV2"]["items"]
                except KeyError:
                    error(f"GitHub API error: {data}")
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
