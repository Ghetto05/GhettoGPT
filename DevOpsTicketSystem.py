import asyncio
import os
import discord
import Database
import WellKnown
from DevOpsClient import AzureDevOpsClient

DEVOPS_ORG = os.getenv("DEVOPS_ORG")
DEVOPS_PROJECT = os.getenv("DEVOPS_PROJECT")
DEVOPS_PAT = os.getenv("DEVOPS_PAT")


azure_devops_client = AzureDevOpsClient(
    org_url=f"https://dev.azure.com/{DEVOPS_ORG}",
    project=DEVOPS_PROJECT,
    pat=DEVOPS_PAT
)


async def handle_thread_creation(thread) -> bool:
    if isinstance(thread.parent, discord.ForumChannel) and thread.parent.id == WellKnown.channel_devops_ticket_system:
        first_message = await thread.fetch_message(thread.id)
        title = thread.name
        description = first_message.content

        # Create Azure DevOps work item (assumes you have a client for this)
        work_item = azure_devops_client.create_work_item(title, description)

        # Save to DB
        await Database.save_mapping(thread.id, work_item['id'])

        await thread.send(f"Issue created in DevOps! Work item ID: {work_item['id']}")
        return True
    else:
        return False


async def handle_message(message: discord.Message) -> bool:
    if message.author.bot:
        return False

    if (isinstance(message.channel, discord.Thread)
            and isinstance(message.channel.parent, discord.ForumChannel)
            and message.channel.parent.id == WellKnown.channel_devops_ticket_system):
        work_item_id = await Database.get_work_item_id(message.channel.id)
        if work_item_id:
            # Add comment to Azure DevOps asynchronously (run in executor if sync)
            await asyncio.get_running_loop().run_in_executor(
                None, lambda: azure_devops_client.add_comment_to_work_item(work_item_id, f"{message.author}: {message.content}")
            )
        return True
    return False
