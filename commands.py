import discord
import discord.ext

from mod_changelog_update import start_webhook_server, run_changelog_update


def setup_commands(bot: discord.ext.commands.Bot):
    bot.loop.create_task(start_webhook_server(bot))

    @bot.slash_command(
        name="update",
        guild_ids=[954740284758032425]
    )
    async def update_command(ctx: discord.ApplicationContext):
        await ctx.send("Updating changelogs...")
        await run_changelog_update(bot)
        await ctx.send("Done.")
