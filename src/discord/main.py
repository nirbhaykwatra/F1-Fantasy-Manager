import discord
from discord.ext import commands
from discord import app_commands
import os
import pathlib
from dotenv import load_dotenv
import asyncio
import logging

from config import load_config

# Run the bot. Note: This must be the last method to be called, owing to the fact that
# it is blocking and will not execute anything after it.

async def main() -> None:
    config = load_config()

    print(config.token)
    # logger = logging.getLogger("bot")

    # Initialize intents
    intents = discord.Intents.none()
    intents.messages = True
    intents.reactions = True
    intents.guilds = True
    intents.members = True
    intents.message_content = True
    intents.emojis_and_stickers = True
    intents.guild_scheduled_events = True

    guild = discord.Object(id=config.guild_id)
    bot = commands.Bot(command_prefix="!", intents=intents)

    # Attach shared services to bot so cogs can access them
    bot.config = config  # type: ignore[attr-defined]
    # bot.db = db          # type: ignore[attr-defined]

    # region Bot Event Handlers

    @bot.event
    async def setup_hook():
        # region Load extensions
        for command in config.cmds_dir.glob("*.py"):
            if command.name != '__init__.py':
                await bot.load_extension(f'commands.{command.name[:-3]}')
        # endregion

    @bot.event
    async def on_ready():
        print("Ready")

    @bot.event
    async def on_message(message):
        message_author = message.author
        message_content = message.content
        if message_author == bot.user:
            return
        await bot.process_commands(message)

    # endregion

    # region Commands

    # Global error handler for command tree
    @bot.tree.error
    async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingRole):
            await interaction.response.send_message(f"You don't have permission to use that command!", ephemeral=True)

    # region Developer message commands
    @bot.group()
    async def dev(ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(f'{ctx.subcommand_passed} is not a valid subcommand.')

    @dev.command(name='sync')
    @commands.has_role('Administrator')
    async def sync_tree(ctx):
        try:
            await bot.tree.sync(guild=guild)
            await ctx.send(f'Command Tree synced for guild {guild.id}.')
        except Exception as e:
            await ctx.send(f'Error syncing command tree: {e}')

    @dev.command(name='reload')
    @commands.has_role('Administrator')
    async def reload_ext(ctx):
        for command in config.cmds_dir.glob("*.py"):
            if command.name != '__init__.py':
                try:
                    await bot.reload_extension(f'commands.{command.name[:-3]}')
                except Exception as e:
                    await ctx.send(f'Error reloading {command.name[:-3]}: {e}')
        await ctx.send(f'Extensions reloaded.')

    # endregion

    # endregion

    try:
        await bot.start(config.token)
    finally:
        pass
        # await db.close()


if __name__ == "__main__":
    asyncio.run(main())