import discord
from discord.ext import commands
from discord import app_commands
import os
import pathlib
from dotenv import load_dotenv

load_dotenv()
# Constants
MODE = os.getenv('MODE')
GUILD_ID = 0
TOKEN = ""
CMDS_DIR = pathlib.Path(__file__).parent/'commands'

if MODE == "DEV":
    GUILD_ID = os.getenv('DEV_GUILD_ID')
    TOKEN = os.getenv('DEV_TOKEN')
elif MODE == "PROD":
    GUILD_ID = os.getenv('GUILD_ID')
    TOKEN = os.getenv('TOKEN')

print(MODE, GUILD_ID, TOKEN)

#region Initialize Intents
intents = discord.Intents.none()
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.members = True
intents.message_content = True
intents.emojis_and_stickers = True
intents.guild_scheduled_events = True
#endregion

#region Bot Setup
guild = discord.Object(id=GUILD_ID)
bot = commands.Bot(command_prefix='!', intents=intents)
#endregion

#region Bot Event Handlers

@bot.event
async def setup_hook():

    #region Load extensions
    for command in CMDS_DIR.glob("*.py"):
        if command.name != '__init__.py':
            await bot.load_extension(f'commands.{command.name[:-3]}')
    #endregion


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
#endregion

#region Commands

# Global error handler for command tree
@bot.tree.error
async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingRole):
        await interaction.response.send_message(f"You don't have permission to use that command!", ephemeral=True)

#region Developer message commands
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
    for command in CMDS_DIR.glob("*.py"):
        if command.name != '__init__.py':
            try:
                await bot.reload_extension(f'commands.{command.name[:-3]}')
            except Exception as e:
                await ctx.send(f'Error reloading {command.name[:-3]}: {e}')
    await ctx.send(f'Extensions reloaded.')
#endregion

#endregion

# Run the bot. Note: This must be the last method to be called, owing to the fact that
# it is blocking and will not execute anything after it.
if __name__ == '__main__':
    bot.run(TOKEN)