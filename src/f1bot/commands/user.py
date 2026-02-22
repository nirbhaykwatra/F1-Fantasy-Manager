from typing import List

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from f1bot.services.choiceservice import ChoiceService
from src.f1bot.config import load_config

config = load_config()

class FantasyUser(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def league_autocomplete(self, interaction: discord.Interaction, current: str) -> List[
        app_commands.Choice[str]]:
        """Autocomplete callback for league choices"""
        return await self.bot.choiceService.get_league_choices(interaction.guild_id)

    @app_commands.command(name='register', description='Register for the league!')
    @app_commands.autocomplete(league=league_autocomplete)
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def register(self, interaction: discord.Interaction, league: str, team_name: str, team_motto: str):
        print(f'Register command invoked for league: {league} with id {int(league)}, team: {team_name}, motto: {team_motto}')

        await interaction.response.send_message(f'This command has not been implemented.', ephemeral=True)

    @app_commands.command(name='draft', description='Draft your team for the selected round!')
    @app_commands.choices()
    @app_commands.guilds(discord.Object(id=config.guild_id))
    async def draft(self, interaction: discord.Interaction, driver1: Choice[str], driver2: Choice[str], driver3: Choice[str], bogey: Choice[str], team: Choice[str]):
        await interaction.response.send_message(f'This command has not been implemented.', ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FantasyUser(bot))

if __name__ == "__main__":
    print