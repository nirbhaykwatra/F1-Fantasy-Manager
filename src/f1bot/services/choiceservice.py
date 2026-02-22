from typing import List

import discord
from discord import app_commands

from f1bot.services.dbservice import DatabaseManager
from src.f1bot.services.models import League, LeagueRepository

class ChoiceService:
    """Service for handling user choices and interactions."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def get_league_choices(self, guild_id: int) -> List[app_commands.Choice]:
        repository = LeagueRepository(self.db)
        leagues = await repository.get_leagues_by_discord_guild(guild_id)
        print(f"Retrieved {len(leagues)} leagues for guild ID: {guild_id}")
        return [app_commands.Choice(name=league.name, value=str(league.id)) for league in leagues]

if __name__ == "__main__":
    import asyncio
    print("ChoiceService module executed as main")
    async def main():
        db = DatabaseManager()
        await db.initialize("postgresql://nirbhaykwatra:31415@192.168.1.240/f1fantasy")
        choice_service = ChoiceService(db)
        print(f"Choice service initialized with database: {db}")
        print(await choice_service.get_league_choices(1116510696742604841))
        print(f"League choices retrieved for guild ID: 1116510696742604841")

    asyncio.run(main())