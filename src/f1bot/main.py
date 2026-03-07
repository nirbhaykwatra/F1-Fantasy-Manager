import asyncio
import discord
from discord.ext import commands
from discord import app_commands

from src.f1bot.config import load_config
from src.f1bot.utils.logger import get_logger, log_event, log_error
from src.f1bot.services.choiceservice import ChoiceService
from src.f1bot.services.dbservice import DatabaseManager
from src.f1bot.services.draftservice import DraftService
from src.f1bot.services.embedservice import EmbedService


async def main() -> None:
    config = load_config()
    logger = get_logger("main")

    logger.info("Starting F1 Fantasy Bot...")
    logger.info(f"Mode: {config.mode}")
    logger.info(f"Guild ID: {config.guild_id}")
    logger.info(f"Season: {config.season}")

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

    # region Bot Event Handlers

    @bot.event
    async def setup_hook():
        logger.info("Running setup hook...")

        # Attach shared services to bot so cogs can access them
        bot.config = config  # type: ignore[attr-defined]

        logger.info("Initializing database connection...")
        bot.db = DatabaseManager()
        await bot.db.initialize(config.database_url, min_size=2, max_size=10)
        logger.info("Database connection established")

        logger.info("Initializing services...")
        bot.choiceService = ChoiceService(db=bot.db)
        bot.draftService = DraftService(db_manager=bot.db)
        bot.embedService = EmbedService()
        logger.info("Services initialized successfully")

        # region Load extensions
        logger.info("Loading command extensions...")
        loaded_count = 0
        for command in config.cmds_dir.glob("*.py"):
            if command.name != '__init__.py':
                try:
                    await bot.load_extension(f'src.f1bot.commands.{command.name[:-3]}')
                    logger.info(f"Loaded extension: {command.name[:-3]}")
                    loaded_count += 1
                except Exception as e:
                    logger.error(f"Failed to load extension {command.name[:-3]}: {e}", exc_info=True)
        logger.info(f"Loaded {loaded_count} command extension(s)")
        # endregion

    @bot.event
    async def on_ready():
        log_event("on_ready", f"Bot logged in as {bot.user} (ID: {bot.user.id})")
        logger.info(f"Connected to {len(bot.guilds)} guild(s)")
        for guild in bot.guilds:
            logger.info(f"  - {guild.name} (ID: {guild.id})")
        logger.info("Bot is ready to receive commands")

    @bot.event
    async def on_message(message):
        message_author = message.author
        message_content = message.content
        if message_author == bot.user:
            return

        if message_content.startswith("!"):
            logger.debug(f"Message command received from {message_author.name}: {message_content}")

        await bot.process_commands(message)

    # endregion

    # region Commands

    # Global error handler for command tree
    @bot.tree.error
    async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        logger.error(
            f"App command error | Command: {interaction.command.name if interaction.command else 'Unknown'} | "
            f"User: {interaction.user.name} (ID: {interaction.user.id}) | Error: {type(error).__name__}: {str(error)}",
            exc_info=True
        )

        if isinstance(error, app_commands.MissingRole):
            await interaction.response.send_message(f"You don't have permission to use that command!", ephemeral=True)
        else:
            await interaction.response.send_message(f"An error occurred while processing the command.", ephemeral=True)

    # region Developer message commands
    @bot.group()
    async def dev(ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(f'{ctx.subcommand_passed} is not a valid subcommand.')

    @dev.command(name='sync')
    @commands.has_role('Administrator')
    async def sync_tree(ctx):
        logger.info(f"Syncing command tree for guild {guild.id} | Requested by: {ctx.author.name}")
        try:
            await bot.tree.sync(guild=guild)
            await ctx.send(f'Command Tree synced for guild {guild.id}.')
            logger.info(f"Command tree synced successfully for guild {guild.id}")
        except Exception as e:
            await ctx.send(f'Error syncing command tree: {e}')
            logger.error(f"Failed to sync command tree for guild {guild.id}: {e}", exc_info=True)

    @dev.command(name='reload')
    @commands.has_role('Administrator')
    async def reload_ext(ctx):
        logger.info(f"Reloading extensions | Requested by: {ctx.author.name}")
        reloaded = []
        failed = []

        for command in config.cmds_dir.glob("*.py"):
            if command.name != '__init__.py':
                try:
                    await bot.reload_extension(f'src.f1bot.commands.{command.name[:-3]}')
                    reloaded.append(command.name[:-3])
                    logger.info(f"Reloaded extension: {command.name[:-3]}")
                except Exception as e:
                    failed.append(command.name[:-3])
                    logger.error(f"Failed to reload extension {command.name[:-3]}: {e}", exc_info=True)
                    await ctx.send(f'Error reloading {command.name[:-3]}: {e}')

        logger.info(f"Extension reload complete | Success: {len(reloaded)} | Failed: {len(failed)}")
        await ctx.send(f'Extensions reloaded. Success: {len(reloaded)}, Failed: {len(failed)}')

    # endregion

    # endregion

    try:
        logger.info("Starting bot connection to Discord...")
        await bot.start(config.token, reconnect=True)
    except KeyboardInterrupt:
        logger.info("Bot shutdown initiated by user (KeyboardInterrupt)")
    except Exception as e:
        logger.critical(f"Critical error during bot execution: {e}", exc_info=True)
    finally:
        logger.info("Bot is shutting down...")
        if hasattr(bot, 'db'):
            logger.info("Closing database connection...")
            await bot.db.close()
            logger.info("Database connection closed")
        logger.info("=" * 80)
        logger.info("F1 Fantasy Bot stopped")
        logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())