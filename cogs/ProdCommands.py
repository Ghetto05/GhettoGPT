from logging import getLogger
from os import environ
from discord import Bot, Cog, slash_command, option, ApplicationContext
import MessageUtils

logger = getLogger(__name__)
is_dev = environ.get("ENV") == "dev"

class ProdCommands(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @slash_command(name="find-all-messages", description="[Test] Find all messages with any of the words given",
                   guild_ids=[954740284758032425])
    @option(
        "words",
        description="The words that should be searched for",
        input_type=str,
        required=True
    )
    async def find_all_messages(self, ctx: ApplicationContext, words: str):
        if is_dev:
            await ctx.respond("This is a production command and must not be used in development!")
            return
        await ctx.respond("Searching for messages...")
        word_list = [w.strip() for w in words.split(",")]
        messages = await MessageUtils.find_messages_with_words(ctx.guild, word_list)

        await ctx.channel.send(content=f"{ctx.author.mention} Found {len(messages)} messages\nDeleting....")
        
        for msg in messages:
            msg.delete(reason="[Bot action] Blacklisted word found")

        await ctx.channel.send(content=f"{ctx.author.mention} Deleted all messages")

def setup(bot: Bot):
    logger.info(f"Registering prod commands")
    bot.add_cog(ProdCommands(bot))