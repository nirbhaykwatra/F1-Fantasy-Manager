import discord
from discord import app_commands
from discord.ext import commands
import os
import pathlib

# TODO: Replace with proper implementation
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

class FantasyUser(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='hello', description='Say hello.')
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def hello(self, interaction: discord.Interaction, name: str):
        await interaction.response.send_message(f'Hello, {name}!', ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FantasyUser(bot))