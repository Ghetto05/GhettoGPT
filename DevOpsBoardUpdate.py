import base64
from datetime import timedelta
from logging import getLogger
from os import getenv
from typing import Optional
from collections import defaultdict
from aiohttp import ClientSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from discord import Bot, Embed, utils

import WellKnown

ORGANIZATION = "ghetto05"
PROJECT = "BladeAndSorceryModding"
AZURE_DEVOPS_PAT = getenv("DEVOPS_TOKEN")
token_bytes = f":{AZURE_DEVOPS_PAT}".encode()
b64_token = base64.b64encode(token_bytes).decode()
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {b64_token}"
}
PAGE_SIZE = 100

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
    logger.info(f"DevOps Board update scheduled to run every {update_interval_minutes} minutes starting at {next_hour} UTC")


async def run_periodic_update():
    try:
        logger.info("Updating DevOps Board")
        await update_board(update_bot)
    except Exception:
        logger.error("Error in updating DevOps board: {e}")


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
    message_content = f"# DevOps Issue Board\nLast update: <t:{int(now.timestamp())}:f>\nNext update: <t:{int(next_run.timestamp())}:R>\n"
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
    issues_by_status = defaultdict(list)
    offset = 0
    has_more = True

    async with ClientSession(headers=HEADERS) as session:
        while has_more:
            wiql_query = {
                "query": f"""
                    SELECT [System.Id], [System.Title], [System.State]
                    FROM WorkItems
                    WHERE [System.TeamProject] = '{PROJECT}'
                    ORDER BY [System.ChangedDate] DESC
                    OFFSET {offset} ROWS
                    FETCH NEXT {PAGE_SIZE} ROWS ONLY
                """
            }

            url_wiql = f"https://dev.azure.com/{ORGANIZATION}/{PROJECT}/_apis/wit/wiql?api-version=7.1-preview.2"

            async with session.post(url_wiql, json=wiql_query) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"WIQL POST failed: {resp.status} {error_text}")
                    break

                data = await resp.json()

            work_items = data.get("workItems", [])
            if not work_items:
                # No more items
                break

            work_item_ids = [str(item["id"]) for item in work_items]

            # Batch get work item details
            ids_param = ",".join(work_item_ids)
            url_wis = f"https://dev.azure.com/{ORGANIZATION}/_apis/wit/workitems?ids={ids_param}&fields=System.Id,System.Title,System.State&api-version=7.1-preview.3"

            async with session.get(url_wis) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"Work items GET failed: {resp.status} {error_text}")
                    break

                items_data = await resp.json()

            for item in items_data.get("value", []):
                fields = item.get("fields", {})
                title = fields.get("System.Title", "No Title")
                number = item.get("id", 0)
                status = fields.get("System.State", "Unknown")

                issues_by_status[status].append({
                    "title": title,
                    "number": number,
                })

            # If fewer than PAGE_SIZE work items returned, finished paging
            if len(work_items) < PAGE_SIZE:
                has_more = False
            else:
                offset += PAGE_SIZE

    return issues_by_status
