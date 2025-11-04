import asyncio
from asyncio import run_coroutine_threadsafe
from logging import getLogger
from os import environ
from threading import Thread
from typing import Optional
from discord import Bot, channel
from flask import Flask, request

import Database
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

@app.route('/webhooks/devops', methods=['POST'])
def devops_webhook():
    if not webhook_bot:
        logger.error("Webhook received but bot is not initialized yet")
        return '', 503

    payload = request.json

    # Parse work item ID
    resource = payload.get('resource', {})
    work_item_id = resource.get('workItemId') or resource.get('id')

    if not work_item_id:
        logger.warning("No work item ID found in webhook payload")
        return '', 400

    # Extract comment if present (adjust based on your webhook payload format)
    # Example: comment text is in resource fields System.History, author in System.ChangedBy
    fields = resource.get('fields', {})
    comment_text = fields.get('System.History')
    author_info = fields.get('System.ChangedBy') or {}
    author_name = author_info.get('displayName', 'Azure DevOps')

    if comment_text:
        thread_id = asyncio.run_coroutine_threadsafe(
            Database.get_thread_id(work_item_id),
            webhook_bot.loop
        ).result()

        if thread_id:
            # Post comment to the Discord thread asynchronously
            future = run_coroutine_threadsafe(
                webhook_bot.get_channel(thread_id).send(f"**{author_name}**:\n{comment_text}"),
                webhook_bot.loop
            )
            try:
                future.result(timeout=10)
            except Exception as exc:
                logger.error(f"Failed to send comment to Discord thread {thread_id}: {exc}")

    return '', 204