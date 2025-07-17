from logging import getLogger
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from discord import Bot
import WellKnown

logger = getLogger(__name__)
update_bot: Optional[Bot] = None


def setup_changelog_summary_scheduler(bot: Bot, scheduler: AsyncIOScheduler):
    global update_bot
    update_bot = bot
    scheduler.add_job(
        send_weekly_changelog_summary,
        CronTrigger(day_of_week='friday', hour=12, minute=0, timezone='UTC')
    )

    # test job
    scheduler.add_job(
        send_weekly_changelog_summary,
        CronTrigger(day_of_week='thursday', hour=8, minute=30, timezone='UTC')
    )


async def send_weekly_changelog_summary():
    channel = update_bot.get_channel(WellKnown.channel_weekly_changelog_update)
    mention = channel.guild.get_role(WellKnown.role_weekly_changelog_update).mention
    await channel.send(f"{mention} weekly changelog summary test")


async def send_changelog_update(bot: Bot):
    channel = bot.get_channel(WellKnown.channel_changelog_update)
    mention = channel.guild.get_role(WellKnown.role_changelog_update).mention
    await channel.send(f"{mention} changelog summary test")