from mod_changelog_update import start_webhook_server, run_changelog_update

def setup_commands(bot):
    bot.loop.create_task(start_webhook_server(bot))

    @bot.tree.command(name="update", description="Update changelogs")
    async def update_command(ctx):
        await ctx.send("🔄 Updating changelogs...")
        await run_changelog_update(bot)
        await ctx.send("✅ Done.")