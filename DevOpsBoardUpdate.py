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
import base64

DEVOPS_ORG = getenv("DEVOPS_ORG")
DEVOPS_PROJECT = getenv("DEVOPS_PROJECT")
DEVOPS_PAT = getenv("DEVOPS_PAT")

logger = getLogger(__name__)
update_bot: Optional[Bot] = None
update_interval_minutes = 10

def setup_board_update(bot: Bot, scheduler: AsyncIOScheduler):
    global update_bot
    update_bot = bot
    next_hour = get_next_interval()
    scheduler.add_job(
        run_periodic_update,
        trigger=IntervalTrigger(minutes=update_interval_minutes, start_date=next_hour)
    )
    logger.info(f"Azure DevOps Board update scheduled to run every {update_interval_minutes} minutes starting at {next_hour} UTC")

async def run_periodic_update():
    try:
        logger.info("Updating Azure DevOps Board")
        await update_board(update_bot)
    except Exception as e:
        logger.error(f"Error in updating Azure DevOps board: {e}", exc_info=True)

def get_next_interval():
    now = utils.utcnow().replace(second=0, microsecond=0)
    minute = (now.minute // update_interval_minutes + 1) * update_interval_minutes
    next_run = now.replace(minute=0) + timedelta(minutes=minute)
    if next_run.minute >= 60:
        next_run = next_run.replace(minute=0) + timedelta(hours=1)
    return next_run

async def update_board(bot: Bot):
    column_issue_groups = await fetch_project_issues()
    now = utils.utcnow()
    next_run = get_next_interval()

    desired_columns = ["To Do", "Urgent", "Doing"]

    message_content = f"# Azure DevOps Board\nLast update: <t:{int(now.timestamp())}:f>\nNext update: <t:{int(next_run.timestamp())}:R>\n"

    for column in desired_columns:
        issues = column_issue_groups.get(column, [])
        if not issues:
            continue
        message_content += f"\n## {column}\n"
        for issue in issues:
            message_content += f"- #{issue['number']}: {issue['title']}\n"

    embed = Embed(description=message_content, color=0xFF4F00)
    message = await bot.get_channel(WellKnown.channel_devops_issue_board).fetch_message(WellKnown.message_devops_issue_board)
    await message.edit(content="", embed=embed)

async def fetch_project_issues():
    basic_auth = base64.b64encode(f":{DEVOPS_PAT}".encode()).decode()
    headers = {
        "Authorization": f"Basic {basic_auth}",
        "Content-Type": "application/json"
    }

    wiql_query = """
    SELECT [System.Id], [System.Title], [System.State] 
    FROM WorkItems 
    WHERE [System.TeamProject] = @project AND [System.WorkItemType] = 'Bug' 
    ORDER BY [System.State] DESC
    """

    async with ClientSession() as session:
        wiql_url = f"https://dev.azure.com/{DEVOPS_ORG}/{DEVOPS_PROJECT}/_apis/wit/wiql?api-version=7.0"
        wiql_payload = {"query": wiql_query}
        async with session.post(wiql_url, json=wiql_payload, headers=headers) as resp:
            resp_json = await resp.json()
            work_items = resp_json.get("workItems", [])
            if not work_items:
                return defaultdict(list)
            ids = [str(wi["id"]) for wi in work_items]

        issues_by_column = defaultdict(list)
        batch_size = 200
        fields_to_fetch = "System.Id,System.Title,System.BoardColumn,System.State"
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i+batch_size]
            ids_str = ",".join(batch_ids)
            items_url = (
                f"https://dev.azure.com/{DEVOPS_ORG}/{DEVOPS_PROJECT}/_apis/wit/workitems"
                f"?ids={ids_str}&fields={fields_to_fetch}&api-version=7.0"
            )
            async with session.get(items_url, headers=headers) as items_resp:
                items_json = await items_resp.json()
                for item in items_json.get("value", []):
                    fields = item.get("fields", {})
                    title = fields.get("System.Title", "No title")
                    number = item.get("id")
                    # Use BoardColumn field if present, else fallback to State
                    column = fields.get("System.BoardColumn") or fields.get("System.State") or "Unknown"
                    issues_by_column[column].append({
                        "title": title,
                        "number": number,
                    })

    return issues_by_column
