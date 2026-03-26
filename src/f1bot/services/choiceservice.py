from typing import List

import discord
from discord import app_commands

from f1bot.services.dbservice import DatabaseManager
from f1bot.services.models import (
    LeagueRepository,
    ConstructorRepository,
    DriverRepository,
    SeasonRepository,
    GrandPrixRepository, CounterpickRepository
)

class ChoiceService:
    """Service for handling user choices and interactions."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def get_league_choices(self, guild_id: int) -> List[app_commands.Choice]:
        repository = LeagueRepository(self.db)
        leagues = await repository.get_leagues_by_discord_guild(guild_id)
        return [app_commands.Choice(name=league.name, value=str(league.id)) for league in leagues]

    async def get_constructor_choices(self, guild_id: int) -> List[app_commands.Choice]:
        season = await SeasonRepository(self.db).get_active_season()
        repository = ConstructorRepository(self.db)
        constructors = await repository.list_constructors_by_season(season.id)
        return [app_commands.Choice(name=constructor.full_name, value=str(constructor.id)) for constructor in constructors]

    async def get_driver_choices(self, guild_id: int) -> List[app_commands.Choice]:
        season = await SeasonRepository(self.db).get_active_season()
        repository = DriverRepository(self.db)
        drivers = await repository.list_drivers_by_season(season.id, active_only=True)
        return [app_commands.Choice(name=str(driver.first_name + ' ' + driver.last_name), value=str(driver.id)) for driver in drivers]

    async def get_grand_prix_choices(self, guild_id: int) -> List[app_commands.Choice]:
        season = await SeasonRepository(self.db).get_active_season()
        repository = GrandPrixRepository(self.db)
        grands_prix = await repository.list_grands_prix_by_season(season.id)
        return [app_commands.Choice(name=str(f"Round {grand_prix.round_number} - {grand_prix.event_name}"), value=str(grand_prix.id)) for grand_prix in grands_prix]

    async def get_counterpick_choices(self, guild_id: int) -> List[app_commands.Choice]:
        season = await SeasonRepository(self.db).get_active_season()
        repository = CounterpickRepository(self.db)
        counterpicks = repository.g

if __name__ == "__main__":
    import asyncio
    from src.f1bot.config import load_config
    async def main():
        config = load_config()
        db = DatabaseManager()
        await db.initialize(config.database_url)
        choice_service = ChoiceService(db)
        print(await choice_service.get_league_choices(1116510696742604841))

    asyncio.run(main())