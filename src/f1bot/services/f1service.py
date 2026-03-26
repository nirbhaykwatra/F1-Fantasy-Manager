"""
Service for querying the Jolpica F1 REST API and upserting data to the local database.
Jolpica F1 API is the successor to the Ergast F1 API with backwards compatible endpoints.
API Base URL: https://api.jolpi.ca/ergast/f1/
"""

import aiohttp
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from f1bot.services.dbservice import DatabaseManager
from f1bot.services.models import (
    SeasonRepository,
    DriverRepository,
    ConstructorRepository,
    GrandPrixRepository,
    Season,
    Driver,
    Constructor,
    GrandPrix
)

logger = logging.getLogger(__name__)


class JolpicaF1Service:
    """
    Service for fetching F1 data from Jolpica API and upserting to local database.
    Provides a repository-like interface with CRUD methods.
    """

    BASE_URL = "https://api.jolpi.ca/ergast/f1"

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.driver_repo = DriverRepository(db_manager)
        self.constructor_repo = ConstructorRepository(db_manager)
        self.grand_prix_repo = GrandPrixRepository(db_manager)
        self.season_repo = SeasonRepository(db_manager)
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry - creates HTTP session"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - closes HTTP session"""
        if self.session:
            await self.session.close()

    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make GET request to Jolpica API

        Args:
            endpoint: API endpoint path
            params: Optional query parameters

        Returns:
            JSON response as dictionary

        Raises:
            aiohttp.ClientError: If request fails
        """
        if not self.session:
            raise RuntimeError("HTTP session not initialized. Use async context manager.")

        url = f"{self.BASE_URL}/{endpoint}"
        logger.info(f"Fetching from Jolpica API: {url}")

        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()
            return data

    # ============================================================
    # DRIVERS
    # ============================================================

    async def fetch_drivers_for_season(self, year: int) -> List[Dict[str, Any]]:
        """
        Fetch all drivers for a specific season from Jolpica API

        Args:
            year: Season year

        Returns:
            List of driver data dictionaries
        """
        try:
            data = await self._get(f"{year}/drivers.json")
            drivers = data.get("MRData", {}).get("DriverTable", {}).get("Drivers", [])
            logger.info(f"Fetched {len(drivers)} drivers for season {year}")
            return drivers
        except Exception as e:
            logger.error(f"Failed to fetch drivers for season {year}: {e}")
            return []

    async def sync_drivers_for_season(self, season_id: int, year: int) -> List[Driver]:
        """
        Fetch drivers from API and upsert to database

        Args:
            season_id: Database season ID
            year: Season year

        Returns:
            List of Driver objects created/updated in database
        """
        api_drivers = await self.fetch_drivers_for_season(year)
        synced_drivers = []

        for driver_data in api_drivers:
            try:
                # Extract driver information
                driver_id: str = driver_data.get("driverId")
                code: str = driver_data.get("code", driver_id[:3].upper())
                number: int = int(driver_data.get("permanentNumber", 0))
                first_name: str = driver_data.get("givenName", "")
                last_name: str = driver_data.get("familyName", "")
                nationality: str = driver_data.get("nationality", "")
                date_of_birth_str: str = driver_data.get("dateOfBirth", "")

                # Parse date of birth
                date_of_birth: datetime = datetime.strptime(date_of_birth_str, "%Y-%m-%d") if date_of_birth_str else None

                # Need to get constructor information separately
                # For now, we'll fetch the constructor mapping from the season's constructor standings
                constructor_id = await self._get_driver_constructor_id(season_id, driver_id, year)

                if constructor_id is None:
                    logger.warning(f"No constructor found for driver {first_name} {last_name} in {year}")
                    continue

                # Check if driver already exists in database
                existing_drivers = await self.driver_repo.list_drivers_by_season(season_id, active_only=False)
                existing_driver = next(
                    (d for d in existing_drivers if d.ergast_id == driver_id),
                    None
                )

                if existing_driver:
                    # Update if constructor changed
                    if existing_driver.constructor_id != constructor_id:
                        await self.driver_repo.update_driver_constructor(existing_driver.id, constructor_id)
                        logger.info(f"Updated constructor for driver {first_name} {last_name}")
                    synced_drivers.append(existing_driver)
                else:
                    # Create new driver
                    driver = await self.driver_repo.create_driver(
                        season_id=season_id,
                        code=code,
                        number=number,
                        first_name=first_name,
                        last_name=last_name,
                        constructor_id=constructor_id,
                        ergast_id=driver_id,
                        is_active=True,
                        nationality=nationality,
                        date_of_birth=date_of_birth
                    )
                    if driver:
                        synced_drivers.append(driver)
                        logger.info(f"Created driver: {first_name} {last_name}")

            except Exception as e:
                logger.error(f"Failed to sync driver {driver_data.get('driverId')}: {e}")

        return synced_drivers

    async def _get_driver_constructor_id(
            self,
            season_id: int,
            driver_ergast_id: str,
            year: int
    ) -> Optional[int]:
        """
        Get the constructor ID for a driver by cross-referencing data from Jolpica

        Args:
            season_id: Database season ID
            driver_ergast_id: Ergast driver ID
            year: Season year

        Returns:
            Constructor database ID or None
        """
        try:
            # Fetch driver's constructor information for the given year
            data = await self._get(f"{year}/drivers/{driver_ergast_id}/constructors.json")
            constructors_data = (
                data.get("MRData", {})
                .get("ConstructorTable", {})
                .get("Constructors", [])
            )


            if constructors_data:
                constructor_ergast_id = constructors_data[0].get("constructorId")

                # Find constructor in database
                constructors = await self.constructor_repo.list_constructors_by_season(season_id)
                constructor = next(
                    (c for c in constructors if c.ergast_id == constructor_ergast_id),
                    None
                )

                if constructor:
                    return constructor.id

            return None

        except Exception as e:
            logger.error(f"Failed to get constructor for driver {driver_ergast_id}: {e}")
            return None

    # ============================================================
    # CONSTRUCTORS
    # ============================================================

    async def fetch_constructors_for_season(self, year: int) -> List[Dict[str, Any]]:
        """
        Fetch all constructors for a specific season from Jolpica API

        Args:
            year: Season year

        Returns:
            List of constructor data dictionaries
        """
        try:
            data = await self._get(f"{year}/constructors.json")
            constructors = data.get("MRData", {}).get("ConstructorTable", {}).get("Constructors", [])
            logger.info(f"Fetched {len(constructors)} constructors for season {year}")
            return constructors
        except Exception as e:
            logger.error(f"Failed to fetch constructors for season {year}: {e}")
            return []

    async def sync_constructors_for_season(
            self,
            season_id: int,
            year: int,
            color_mapping: Optional[Dict[str, str]] = None
    ) -> List[Constructor]:
        """
        Fetch constructors from API and upsert to database

        Args:
            season_id: Database season ID
            year: Season year
            color_mapping: Optional dict mapping constructor IDs to hex colors

        Returns:
            List of Constructor objects created/updated in database
        """
        api_constructors = await self.fetch_constructors_for_season(year)
        synced_constructors = []

        # Default color mapping (can be overridden)
        default_colors = {
            "alpine": "#ed4099",
            "aston_martin": "#229971",
            "audi": "#ff2d00",
            "cadillac": "#3b3b3b",
            "ferrari": "#e80000",
            "haas": "#dee1e2",
            "mclaren": "#ff8000",
            "mercedes": "#27f4d2",
            "rb": "#6692ff",
            "red_bull": "#0d02ad",
            "williams": "#1868db"
        }

        full_names = {
            "alpine": "BWT Alpine Formula One Team",
            "aston_martin": "Aston Martin Aramco Formula One Team",
            "audi": "Audi Revolut F1 Team",
            "cadillac": "Cadillac Formula 1 Team",
            "ferrari": "Scuderia Ferrari HP",
            "haas": "TGR Haas F1 Team",
            "mclaren": "McLaren Mastercard F1 Team",
            "mercedes": "Mercedes-AMG PETRONAS Formula One Team",
            "rb": "Visa Cash App Racing Bulls Formula One Team",
            "red_bull": "Oracle Red Bull Racing",
            "williams": "Atlassian Williams F1 Team"
        }
        colors = color_mapping or default_colors

        for constructor_data in api_constructors:
            try:
                constructor_id: str = constructor_data.get("constructorId")
                full_name = full_names.get(constructor_id, constructor_data.get("name", ""))
                short_name = constructor_data.get("name", "")

                # Remove "F1 Team" from short name if present
                short_name = short_name.replace("F1 Team", "")

                color_hex = colors.get(constructor_id, "#FFFFFF")

                # Check if constructor exists
                existing_constructors = await self.constructor_repo.list_constructors_by_season(season_id)
                existing_constructor = next(
                    (c for c in existing_constructors if c.ergast_id == constructor_id),
                    None
                )

                if existing_constructor:
                    # Update if needed
                    await self.constructor_repo.update_constructor(
                        constructor_id=existing_constructor.id,
                        short_name=short_name,
                        full_name=full_name,
                        color_hex=color_hex,
                        ergast_id=constructor_id
                    )
                    synced_constructors.append(existing_constructor)
                    logger.info(f"Updated constructor: {full_name}")
                else:
                    # Create new constructor
                    constructor = await self.constructor_repo.create_constructor(
                        season_id=season_id,
                        short_name=short_name,
                        full_name=full_name,
                        color_hex=color_hex,
                        ergast_id=constructor_id
                    )
                    if constructor:
                        synced_constructors.append(constructor)
                        logger.info(f"Created constructor: {full_name}")

            except Exception as e:
                logger.error(f"Failed to sync constructor {constructor_data.get('constructorId')}: {e}")

        return synced_constructors

    # ============================================================
    # GRANDS PRIX / RACES
    # ============================================================

    async def fetch_race_schedule_for_season(self, year: int) -> List[Dict[str, Any]]:
        """
        Fetch race schedule/calendar for a specific season from Jolpica API

        Args:
            year: Season year

        Returns:
            List of race data dictionaries
        """
        try:
            data = await self._get(f"{year}.json")
            races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
            logger.info(f"Fetched {len(races)} races for season {year}")
            return races
        except Exception as e:
            logger.error(f"Failed to fetch race schedule for season {year}: {e}")
            return []

    async def sync_grands_prix_for_season(
            self,
            season_id: int,
            year: int
    ) -> List[GrandPrix]:
        """
        Fetch race schedule from API and upsert to database
        Automatically detects sprint format rounds based on API data

        Args:
            season_id: Database season ID
            year: Season year

        Returns:
            List of GrandPrix objects created/updated in database
        """
        api_races = await self.fetch_race_schedule_for_season(year)
        synced_races = []

        for race_data in api_races:
            try:
                round_number = int(race_data.get("round", 0))
                event_name = race_data.get("raceName", "")
                circuit_key = race_data.get("Circuit", {}).get("circuitId")

                # Automatically determine event format based on presence of Sprint data
                event_format = "sprint_qualifying" if "Sprint" in race_data else "conventional"

                draft_deadline_utc = None
                draft_reset_utc = None
                counterpick_deadline_utc = None

                # Parse race date
                race_date_str = race_data.get("date")
                race_time_str = race_data.get("time", "00:00:00Z")
                race_date_utc = None
                if race_date_str:
                    datetime_str = f"{race_date_str}T{race_time_str}"
                    race_date_utc = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
                    draft_reset_utc = race_date_utc + timedelta(hours=3)

                # Parse qualifying date (if available)
                quali_date_utc = None
                if "Qualifying" in race_data:
                    quali_date_str = race_data["Qualifying"].get("date")
                    quali_time_str = race_data["Qualifying"].get("time", "00:00:00Z")
                    if quali_date_str:
                        datetime_str = f"{quali_date_str}T{quali_time_str}"
                        quali_date_utc = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
                        draft_deadline_utc = quali_date_utc
                        counterpick_deadline_utc = quali_date_utc - timedelta(days=3)

                # Parse sprint date (if available)
                sprint_date_utc = None
                if "Sprint" in race_data:
                    sprint_date_str = race_data["Sprint"].get("date")
                    sprint_time_str = race_data["Sprint"].get("time", "00:00:00Z")
                    if sprint_date_str:
                        datetime_str = f"{sprint_date_str}T{sprint_time_str}"
                        sprint_date_utc = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))

                # Parse sprint qualifying date (if available)
                sprint_qualifying_date_utc = None
                if "SprintQualifying" in race_data:
                    sprint_qualifying_date_str = race_data["SprintQualifying"].get("date")
                    sprint_qualifying_time_str = race_data["SprintQualifying"].get("time", "00:00:00Z")
                    if sprint_qualifying_date_str:
                        datetime_str = f"{sprint_qualifying_date_str}T{sprint_qualifying_time_str}"
                        sprint_qualifying_date_utc = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
                        draft_deadline_utc = sprint_qualifying_date_utc
                        counterpick_deadline_utc = sprint_qualifying_date_utc - timedelta(days=3)

                # Check if grand prix exists
                existing_gps = await self.grand_prix_repo.list_grands_prix_by_season(season_id)
                existing_gp = next(
                    (gp for gp in existing_gps if gp.round_number == round_number),
                    None
                )

                if existing_gp:
                    # Update dates if needed
                    await self.grand_prix_repo.update_grand_prix_dates(
                        grand_prix_id=existing_gp.id,
                        quali_date_utc=quali_date_utc,
                        sprint_date_utc=sprint_date_utc,
                        sprint_quali_date_utc=sprint_qualifying_date_utc,
                        race_date_utc=race_date_utc,
                        draft_deadline_utc=draft_deadline_utc,
                        draft_reset_utc=draft_reset_utc,
                        counterpick_deadline_utc=counterpick_deadline_utc
                    )
                    synced_races.append(existing_gp)
                    logger.info(f"Updated Grand Prix: {event_name}")
                else:
                    # Create new grand prix
                    gp = await self.grand_prix_repo.create_grand_prix(
                        season_id=season_id,
                        round_number=round_number,
                        event_name=event_name,
                        circuit_key=circuit_key,
                        event_format=event_format,
                        quali_date_utc=quali_date_utc,
                        sprint_quali_date_utc=sprint_qualifying_date_utc,
                        sprint_date_utc=sprint_date_utc,
                        race_date_utc=race_date_utc,
                        draft_deadline_utc=draft_deadline_utc,
                        draft_reset_utc=draft_reset_utc,
                        counterpick_deadline_utc=counterpick_deadline_utc,
                        is_completed=False
                    )
                    if gp:
                        synced_races.append(gp)
                        logger.info(f"Created Grand Prix: {event_name}")

            except Exception as e:
                logger.error(f"Failed to sync race {race_data.get('raceName')}: {e}")

        return synced_races

    # ============================================================
    # BATCH SYNC OPERATIONS
    # ============================================================

    async def sync_season_data(
            self,
            year: int,
            constructor_colors: Optional[Dict[str, str]] = None
    ) -> Dict[str, List]:
        """
        Sync all data (constructors, drivers, races) for a season
        Sprint rounds are automatically detected from API data

        Args:
            season_id: Database season ID
            year: Season year
            constructor_colors: Optional color mapping for constructors

        Returns:
            Dictionary with lists of synced objects by type
        """
        season: Season = await self.season_repo.get_season_by_year(year)
        if not season:
            raise ValueError(f"Season {year} not found")

        season_id: int = season.id if season else None
        logger.info(f"Starting full sync for season {year} (ID: {season_id})")


        # Sync in order: constructors first (drivers depend on them)
        constructors = await self.sync_constructors_for_season(season_id, year, constructor_colors)
        drivers = await self.sync_drivers_for_season(season_id, year)
        races = await self.sync_grands_prix_for_season(season_id, year)

        logger.info(
            f"Sync complete for season {year}: "
            f"{len(constructors)} constructors, "
            f"{len(drivers)} drivers, "
            f"{len(races)} races"
        )

        return {
            "constructors": constructors,
            "drivers": drivers,
            "races": races
        }


# ============================================================
# STANDALONE USAGE EXAMPLE
# ============================================================

if __name__ == "__main__":
    import asyncio
    from src.f1bot.services.models import SeasonRepository
    from src.f1bot.config import load_config

    async def main():
        """Example usage of JolpicaF1Service"""

        config = load_config()
        db = DatabaseManager()
        await db.initialize(config.database_url)

        # Create or get season
        season_repo = SeasonRepository(db)
        season = await season_repo.get_season_by_year(2026)
        if not season:
            season = await season_repo.create_season(2026, is_active=True)

        # Sync all data for 2024 season
        async with JolpicaF1Service(db) as f1_service:
            result = await f1_service.sync_season_data(year=2026)

            print(f"Synced {len(result['constructors'])} constructors")
            print(f"Synced {len(result['drivers'])} drivers")
            print(f"Synced {len(result['races'])} races")

        await db.close()


    asyncio.run(main())