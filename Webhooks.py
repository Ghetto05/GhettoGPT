from asyncio import run_coroutine_threadsafe
from logging import getLogger
from os import environ
from threading import Thread
from typing import Optional
from discord import Bot, channel
from flask import Flask
from GitHubChangelogUpdate import changelog_update

import WellKnown

flask_started = False
logger = getLogger(__name__)
app = Flask(__name__)
webhook_output_channel: Optional[channel] = None
webhook_bot: Optional[Bot] = None
is_dev = environ.get("ENV") == "dev"


async def setup_webhooks(bot: Bot):
    global flask_started, webhook_output_channel, webhook_bot
    logger.info("Setting up webhooks")
    webhook_bot = bot
    webhook_output_channel = bot.get_channel(WellKnown.channel_bot_setup)
    if not flask_started:
        Thread(target=run_flask, daemon=True).start()
        flask_started = True


def run_flask():
    app.run(host="0.0.0.0", port=5000)


@app.route('/webhooks/discord-bot/changelog-update', methods=['POST'])
def changelog_webhook():
    if is_dev:
        return '', 204
    logger.info("Change log update webhook triggered")
    if webhook_output_channel:
        run_coroutine_threadsafe(
            changelog_update(),
            webhook_bot.loop
        )
    return '', 204