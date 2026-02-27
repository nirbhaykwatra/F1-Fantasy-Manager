from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from src.f1bot.services.dbservice import DatabaseManager


# ============================================================
# DATACLASSES
# ============================================================

@dataclass
class Season:
    """Represents a season (e.g., 2024, 2025)"""
    id: int
    year: int
    is_active: bool
    created_at: datetime


@dataclass
class Constructor:
    """Represents a constructor/team for a season"""
    id: int
    season_id: int
    short_name: str
    full_name: str
    color_hex: str
    ergast_id: Optional[str]


@dataclass
class Driver:
    """Represents a driver for a season"""
    id: int
    season_id: int
    code: str
    number: int
    first_name: str
    last_name: str
    constructor_id: int
    ergast_id: Optional[str]
    is_active: bool
    date_of_birth: Optional[datetime]
    nationality: Optional[str]
    driver_image_url: Optional[str]


@dataclass
class GrandPrix:
    """Represents a Grand Prix event"""
    id: int
    season_id: int
    round_number: int
    event_name: str
    circuit_key: Optional[str]
    event_format: str
    quali_date_utc: Optional[datetime]
    sprint_quali_date_utc: Optional[datetime]
    sprint_date_utc: Optional[datetime]
    race_date_utc: Optional[datetime]
    draft_deadline_utc: Optional[datetime]
    draft_reset_utc: Optional[datetime]
    counterpick_deadline_utc: Optional[datetime]
    is_completed: bool


@dataclass
class League:
    """Represents a fantasy league"""
    id: int
    name: str
    discord_guild_id: Optional[int]
    season_id: int
    embed_color: int
    created_at: datetime
    counterpick_limit: int = 3


@dataclass
class Player:
    """Represents a player in the fantasy league"""
    id: int
    discord_user_id: Optional[int]
    username: str
    password: Optional[str]
    timezone: str
    created_at: datetime


@dataclass
class PlayerLeague:
    """Represents a player's membership in a league"""
    player_id: int
    league_id: int
    team_name: Optional[str]
    team_motto: Optional[str]
    joined_at: datetime


@dataclass
class Draft:
    """Represents a player's draft for a Grand Prix in a specific league"""
    id: int
    player_id: int
    league_id: int
    grand_prix_id: int
    driver1_id: int
    driver2_id: int
    driver3_id: int
    wildcard_id: int
    constructor_id: int
    is_auto_assigned: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class DriverExhaustion:
    """Tracks consecutive driver usage for exhaustion rules"""
    id: int
    player_id: int
    league_id: int
    driver_id: int
    last_grand_prix_id: int
    consecutive_uses: int
    is_exhausted: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class Counterpick:
    """Represents a counterpick (driver ban) in a specific league"""
    id: int
    grand_prix_id: int
    league_id: int
    picking_player_id: int
    target_player_id: int
    target_driver_id: int
    created_at: datetime

@dataclass
class CounterpickUsage:
    """Tracks counterpick usage per player per league per season"""
    player_id: int
    league_id: int
    season_id: int
    used_count: int

@dataclass
class RaceResult:
    """Represents race results for a session"""
    id: int
    grand_prix_id: int
    session_type: str
    driver_id: int
    position: int


@dataclass
class PlayerRoundScore:
    """Represents a player's score for a Grand Prix in a specific league"""
    id: int
    player_id: int
    league_id: int
    grand_prix_id: int
    total_points: int
    breakdown_json: Dict[str, Any]
    calculated_at: datetime


@dataclass
class ScoringRule:
    """Represents a scoring rule for a season"""
    id: int
    season_id: int
    rule_key: str
    rule_value: Any  # JSONB field


# ============================================================
# REPOSITORIES
# ============================================================

class SeasonRepository:
    """Handles all database operations for seasons"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def create_season(self, year: int, is_active: bool = False) -> Optional[Season]:
        """CREATE: Add a new season"""
        query = """
                INSERT INTO seasons (year, is_active)
                VALUES (%s, %s) RETURNING id, year, is_active, created_at
                """
        try:
            row = await self.db.fetch_one(query, (year, is_active))
            return Season(*row) if row else None
        except Exception as e:
            raise ValueError(f"Season creation failed: {e}")

    async def get_season_by_id(self, season_id: int) -> Optional[Season]:
        """READ: Get season by ID"""
        query = """
                SELECT id, year, is_active, created_at
                FROM seasons
                WHERE id = %s
                """
        row = await self.db.fetch_one(query, (season_id,))
        return Season(*row) if row else None

    async def get_active_season(self) -> Optional[Season]:
        """READ: Get the currently active season"""
        query = """
                SELECT id, year, is_active, created_at
                FROM seasons
                WHERE is_active = TRUE
                """
        row = await self.db.fetch_one(query)
        return Season(*row) if row else None

    async def get_season_by_year(self, year: int) -> Optional[Season]:
        """READ: Get season by year"""
        query = """
                SELECT id, year, is_active, created_at
                FROM seasons
                WHERE year = %s
                """
        row = await self.db.fetch_one(query, (year,))
        return Season(*row) if row else None

    async def set_active_season(self, season_id: int) -> bool:
        """UPDATE: Set a season as active (deactivates all others)"""
        query = """
                UPDATE seasons
                SET is_active = (id = %s)
                """
        await self.db.execute_query(query, (season_id,))
        return True

    async def list_all_seasons(self) -> List[Season]:
        """READ: Get all seasons"""
        query = """
                SELECT id, year, is_active, created_at
                FROM seasons
                ORDER BY year DESC
                """
        rows = await self.db.fetch_all(query)
        return [Season(*row) for row in rows]


class ConstructorRepository:
    """Handles all database operations for constructors"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def create_constructor(
            self,
            season_id: int,
            short_name: str,
            full_name: str,
            color_hex: str = '#FFFFFF',
            ergast_id: Optional[str] = None
    ) -> Optional[Constructor]:
        """CREATE: Add a new constructor"""
        query = """
                INSERT INTO constructors (season_id, short_name, full_name, color_hex, ergast_id)
                VALUES (%s, %s, %s, %s, %s) RETURNING id, season_id, short_name, full_name, color_hex, ergast_id
                """
        try:
            row = await self.db.fetch_one(query, (season_id, short_name, full_name, color_hex, ergast_id))
            return Constructor(*row) if row else None
        except Exception as e:
            raise ValueError(f"Constructor creation failed: {e}")

    async def get_constructor_by_id(self, constructor_id: int) -> Optional[Constructor]:
        """READ: Get constructor by ID"""
        query = """
                SELECT id, season_id, short_name, full_name, color_hex, ergast_id
                FROM constructors
                WHERE id = %s
                """
        row = await self.db.fetch_one(query, (constructor_id,))
        return Constructor(*row) if row else None

    async def list_constructors_by_season(self, season_id: int) -> List[Constructor]:
        """READ: Get all constructors for a season"""
        query = """
                SELECT id, season_id, short_name, full_name, color_hex, ergast_id
                FROM constructors
                WHERE season_id = %s
                ORDER BY short_name
                """
        rows = await self.db.fetch_all(query, (season_id,))
        return [Constructor(*row) for row in rows]

    async def update_constructor(
            self,
            constructor_id: int,
            short_name: Optional[str] = None,
            full_name: Optional[str] = None,
            color_hex: Optional[str] = None,
            ergast_id: Optional[str] = None
    ) -> bool:
        """UPDATE: Update constructor details"""
        updates = []
        params = []

        if short_name is not None:
            updates.append("short_name = %s")
            params.append(short_name)
        if full_name is not None:
            updates.append("full_name = %s")
            params.append(full_name)
        if color_hex is not None:
            updates.append("color_hex = %s")
            params.append(color_hex)
        if ergast_id is not None:
            updates.append("ergast_id = %s")
            params.append(ergast_id)

        if not updates:
            return False

        params.append(constructor_id)
        query = f"UPDATE constructors SET {', '.join(updates)} WHERE id = %s"
        await self.db.execute_query(query, tuple(params))
        return True

    async def delete_constructor(self, constructor_id: int) -> bool:
        """DELETE: Remove a constructor"""
        query = "DELETE FROM constructors WHERE id = %s"
        await self.db.execute_query(query, (constructor_id,))
        return True


class DriverRepository:
    """Handles all database operations for drivers"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def create_driver(
            self,
            season_id: int,
            code: str,
            number: int,
            first_name: str,
            last_name: str,
            constructor_id: int,
            ergast_id: Optional[str] = None,
            is_active: bool = True,
            date_of_birth: Optional[datetime] = None,
            nationality: Optional[str] = None,
            driver_image_url: Optional[str] = None
    ) -> Optional[Driver]:
        """CREATE: Add a new driver"""
        query = """
                INSERT INTO drivers (season_id, code, number, first_name, last_name, constructor_id, ergast_id, \
                                     is_active, date_of_birth, nationality, driver_image_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, \
                        %s) RETURNING id, season_id, code, number, first_name, last_name, constructor_id, ergast_id, is_active, date_of_birth, nationality, driver_image_url
                """
        try:
            row = await self.db.fetch_one(query,
                                          (season_id, code, number, first_name, last_name, constructor_id, ergast_id,
                                           is_active, date_of_birth, nationality, driver_image_url))
            return Driver(*row) if row else None
        except Exception as e:
            raise ValueError(f"Driver creation failed: {e}")

    async def get_driver_by_id(self, driver_id: int) -> Optional[Driver]:
        """READ: Get driver by ID"""
        query = """
                SELECT id, \
                       season_id, \
                       code, \
                       number, \
                       first_name, \
                       last_name, \
                       constructor_id, \
                       ergast_id, \
                       is_active, \
                       date_of_birth, \
                       nationality, \
                       driver_image_url
                FROM drivers
                WHERE id = %s
                """
        row = await self.db.fetch_one(query, (driver_id,))
        return Driver(*row) if row else None

    async def get_driver_by_code(self, season_id: int, code: str) -> Optional[Driver]:
        """READ: Get driver by code"""
        query = """
                SELECT id, \
                       season_id, \
                       code, \
                       number, \
                       first_name, \
                       last_name, \
                       constructor_id, \
                       ergast_id, \
                       is_active, \
                       date_of_birth, \
                       nationality, \
                       driver_image_url
                FROM drivers
                WHERE season_id = %s AND code = %s \
                """
        row = await self.db.fetch_one(query, (season_id, code))
        return Driver(*row) if row else None

    async def list_drivers_by_season(self, season_id: int, active_only: bool = True) -> List[Driver]:
        """READ: Get all drivers for a season"""
        query = """
                SELECT id, \
                       season_id, \
                       code, \
                       number, \
                       first_name, \
                       last_name, \
                       constructor_id, \
                       ergast_id, \
                       is_active, \
                       date_of_birth, \
                       nationality, \
                       driver_image_url
                FROM drivers
                WHERE season_id = %s
                """
        if active_only:
            query += " AND is_active = TRUE"
        query += " ORDER BY last_name, first_name"

        rows = await self.db.fetch_all(query, (season_id,))
        return [Driver(*row) for row in rows]

    async def list_drivers_by_constructor(self, constructor_id: int) -> List[Driver]:
        """READ: Get all drivers for a constructor"""
        query = """
                SELECT id, \
                       season_id, \
                       code, \
                       number, \
                       first_name, \
                       last_name, \
                       constructor_id, \
                       ergast_id, \
                       is_active, \
                       date_of_birth, \
                       nationality, \
                       driver_image_url
                FROM drivers
                WHERE constructor_id = %s \
                  AND is_active = TRUE
                ORDER BY last_name, first_name
                """
        rows = await self.db.fetch_all(query, (constructor_id,))
        return [Driver(*row) for row in rows]

    async def update_driver_constructor(self, driver_id: int, constructor_id: int) -> bool:
        """UPDATE: Update driver's constructor (for mid-season transfers)"""
        query = """
                UPDATE drivers
                SET constructor_id = %s
                WHERE id = %s
                """
        await self.db.execute_query(query, (constructor_id, driver_id))
        return True

    async def set_driver_active_status(self, driver_id: int, is_active: bool) -> bool:
        """UPDATE: Set driver's active status"""
        query = """
                UPDATE drivers
                SET is_active = %s
                WHERE id = %s
                """
        await self.db.execute_query(query, (is_active, driver_id))
        return True

    async def delete_driver(self, driver_id: int) -> bool:
        """DELETE: Remove a driver"""
        query = "DELETE FROM drivers WHERE id = %s"
        await self.db.execute_query(query, (driver_id,))
        return True


class GrandPrixRepository:
    """Handles all database operations for grands prix"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def create_grand_prix(
            self,
            season_id: int,
            round_number: int,
            event_name: str,
            circuit_key: Optional[str] = None,
            event_format: str = 'conventional',
            quali_date_utc: Optional[datetime] = None,
            sprint_quali_date_utc: Optional[datetime] = None,
            sprint_date_utc: Optional[datetime] = None,
            race_date_utc: Optional[datetime] = None,
            draft_deadline_utc: Optional[datetime] = None,
            draft_reset_utc: Optional[datetime] = None,
            counterpick_deadline_utc: Optional[datetime] = None,
            is_completed: bool = False
    ) -> Optional[GrandPrix]:
        """CREATE: Add a new Grand Prix"""
        query = """
                INSERT INTO grands_prix (season_id, round_number, event_name, circuit_key, event_format,
                                         quali_date_utc, sprint_quali_date_utc, sprint_date_utc, race_date_utc,
                                         draft_deadline_utc, draft_reset_utc, counterpick_deadline_utc, is_completed)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                RETURNING id, season_id, round_number, event_name, circuit_key, event_format,
                          quali_date_utc, sprint_quali_date_utc, sprint_date_utc, race_date_utc,
                          draft_deadline_utc, draft_reset_utc, counterpick_deadline_utc, is_completed
                """
        try:
            row = await self.db.fetch_one(query, (
                season_id, round_number, event_name, circuit_key, event_format,
                quali_date_utc, sprint_quali_date_utc, sprint_date_utc, race_date_utc,
                draft_deadline_utc, draft_reset_utc, counterpick_deadline_utc, is_completed
            ))
            return GrandPrix(*row) if row else None
        except Exception as e:
            raise ValueError(f"Grand Prix creation failed: {e}")

    async def get_grand_prix_by_id(self, grand_prix_id: int) -> Optional[GrandPrix]:
        """READ: Get Grand Prix by ID"""
        query = """
                SELECT id, season_id, round_number, event_name, circuit_key, event_format,
                       quali_date_utc, sprint_quali_date_utc, sprint_date_utc, race_date_utc,
                       draft_deadline_utc, draft_reset_utc, counterpick_deadline_utc, is_completed
                FROM grands_prix
                WHERE id = %s
                """
        row = await self.db.fetch_one(query, (grand_prix_id,))
        return GrandPrix(*row) if row else None

    async def list_grands_prix_by_season(self, season_id: int) -> List[GrandPrix]:
        """READ: Get all Grand Prix events for a season"""
        query = """
                SELECT id, season_id, round_number, event_name, circuit_key, event_format,
                       quali_date_utc, sprint_quali_date_utc, sprint_date_utc, race_date_utc,
                       draft_deadline_utc, draft_reset_utc, counterpick_deadline_utc, is_completed
                FROM grands_prix
                WHERE season_id = %s
                ORDER BY round_number
                """
        rows = await self.db.fetch_all(query, (season_id,))
        return [GrandPrix(*row) for row in rows]

    async def get_next_grand_prix(self, season_id: int) -> Optional[GrandPrix]:
        """READ: Get the next upcoming Grand Prix"""
        query = """
                SELECT id, season_id, round_number, event_name, circuit_key, event_format,
                       quali_date_utc, sprint_quali_date_utc, sprint_date_utc, race_date_utc,
                       draft_deadline_utc, draft_reset_utc, counterpick_deadline_utc, is_completed
                FROM grands_prix
                WHERE season_id = %s AND is_completed = FALSE
                ORDER BY round_number LIMIT 1
                """
        row = await self.db.fetch_one(query, (season_id,))
        return GrandPrix(*row) if row else None

    async def mark_as_completed(self, grand_prix_id: int) -> bool:
        """UPDATE: Mark a Grand Prix as completed"""
        query = """
                UPDATE grands_prix
                SET is_completed = TRUE
                WHERE id = %s
                """
        await self.db.execute_query(query, (grand_prix_id,))
        return True

    async def update_grand_prix_dates(
            self,
            grand_prix_id: int,
            quali_date_utc: Optional[datetime] = None,
            sprint_quali_date_utc: Optional[datetime] = None,
            sprint_date_utc: Optional[datetime] = None,
            race_date_utc: Optional[datetime] = None,
            draft_deadline_utc: Optional[datetime] = None,
            draft_reset_utc: Optional[datetime] = None,
            counterpick_deadline_utc: Optional[datetime] = None
    ) -> bool:
        """UPDATE: Update Grand Prix dates"""
        updates = []
        params = []

        if quali_date_utc is not None:
            updates.append("quali_date_utc = %s")
            params.append(quali_date_utc)
        if sprint_quali_date_utc is not None:
            updates.append("sprint_quali_date_utc = %s")
            params.append(sprint_quali_date_utc)
        if sprint_date_utc is not None:
            updates.append("sprint_date_utc = %s")
            params.append(sprint_date_utc)
        if race_date_utc is not None:
            updates.append("race_date_utc = %s")
            params.append(race_date_utc)
        if draft_deadline_utc is not None:
            updates.append("draft_deadline_utc = %s")
            params.append(draft_deadline_utc)
        if draft_reset_utc is not None:
            updates.append("draft_reset_utc = %s")
            params.append(draft_reset_utc)
        if counterpick_deadline_utc is not None:
            updates.append("counterpick_deadline_utc = %s")
            params.append(counterpick_deadline_utc)

        if not updates:
            return False

        params.append(grand_prix_id)
        query = f"UPDATE grands_prix SET {', '.join(updates)} WHERE id = %s"
        await self.db.execute_query(query, tuple(params))
        return True

    async def delete_grand_prix(self, grand_prix_id: int) -> bool:
        """DELETE: Remove a Grand Prix"""
        query = "DELETE FROM grands_prix WHERE id = %s"
        await self.db.execute_query(query, (grand_prix_id,))
        return True


class LeagueRepository:
    """Handles all database operations for leagues"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def create_league(
            self,
            name: str,
            season_id: int,
            discord_guild_id: Optional[int] = None,
            embed_color: int = 15135274,
            counterpick_limit: int = 3
    ) -> Optional[League]:
        """CREATE: Add a new league"""
        query = """
                INSERT INTO leagues (name, discord_guild_id, season_id, embed_color, counterpick_limit)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, name, discord_guild_id, season_id, embed_color, created_at, counterpick_limit
                """
        try:
            row = await self.db.fetch_one(query, (name, discord_guild_id, season_id, embed_color, counterpick_limit))
            return League(*row) if row else None
        except Exception as e:
            raise ValueError(f"League creation failed: {e}")

    async def get_league_by_id(self, league_id: int) -> Optional[League]:
        """READ: Get league by ID"""
        query = """
                SELECT id, name, discord_guild_id, season_id, embed_color, created_at, counterpick_limit
                FROM leagues
                WHERE id = %s
                """
        row = await self.db.fetch_one(query, (league_id,))
        return League(*row) if row else None

    async def get_league_by_discord_guild(self, discord_guild_id: int) -> Optional[League]:
        """READ: Get league by Discord guild ID (returns first if multiple exist)"""
        query = """
                SELECT id, name, discord_guild_id, season_id, embed_color, created_at, counterpick_limit
                FROM leagues
                WHERE discord_guild_id = %s
                LIMIT 1
                """
        row = await self.db.fetch_one(query, (discord_guild_id,))
        return League(*row) if row else None

    async def get_leagues_by_discord_guild(self, discord_guild_id: int) -> List[League]:
        """READ: Get all leagues for a Discord guild"""
        query = """
                SELECT id, name, discord_guild_id, season_id, embed_color, created_at, counterpick_limit
                FROM leagues
                WHERE discord_guild_id = %s
                ORDER BY created_at DESC
                """
        rows = await self.db.fetch_all(query, (discord_guild_id,))
        return [League(*row) for row in rows]

    async def list_leagues_by_season(self, season_id: int) -> List[League]:
        """READ: Get all leagues for a season"""
        query = """
                SELECT id, name, discord_guild_id, season_id, embed_color, created_at, counterpick_limit
                FROM leagues
                WHERE season_id = %s
                ORDER BY created_at DESC
                """
        rows = await self.db.fetch_all(query, (season_id,))
        return [League(*row) for row in rows]

    async def get_player_count(self, league_id: int) -> int:
        """READ: Get the number of players in a league"""
        query = """
                SELECT COUNT(*)
                FROM player_leagues
                WHERE league_id = %s
                """
        row = await self.db.fetch_one(query, (league_id,))
        return row[0] if row else 0

    async def list_players_in_league(self, league_id: int) -> List[Player]:
        """READ: Get all players in a league (convenience method)"""
        query = """
                SELECT p.id, p.discord_user_id, p.username, p.password, p.team_name, p.team_motto, p.timezone, p.created_at
                FROM players p
                JOIN player_leagues pl ON pl.player_id = p.id
                WHERE pl.league_id = %s
                ORDER BY pl.joined_at
                """
        rows = await self.db.fetch_all(query, (league_id,))
        return [Player(*row) for row in rows]

    async def update_league_name(self, league_id: int, name: str) -> bool:
        """UPDATE: Update league name"""
        query = """
                UPDATE leagues
                SET name = %s
                WHERE id = %s
                """
        await self.db.execute_query(query, (name, league_id))
        return True

    async def update_league_counterpick_limit(self, league_id: int, counterpick_limit: int) -> bool:
        """UPDATE: Update league's counterpick limit"""
        query = """
                UPDATE leagues
                SET counterpick_limit = %s
                WHERE id = %s
                """
        await self.db.execute_query(query, (counterpick_limit, league_id))
        return True

    async def delete_league(self, league_id: int) -> bool:
        """DELETE: Remove a league"""
        query = "DELETE FROM leagues WHERE id = %s"
        await self.db.execute_query(query, (league_id,))
        return True


class PlayerRepository:
    """Handles all database operations for players"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def create_player(
            self,
            username: str,
            discord_user_id: Optional[int] = None,
            password: Optional[str] = None,
            timezone: str = "UTC"
    ) -> Optional[Player]:
        """CREATE: Register a new player (without league association)"""
        query = """
                INSERT INTO players (discord_user_id, username, password, timezone)
                VALUES (%s, %s, %s, \
                        %s) RETURNING id, discord_user_id, username, password, timezone, created_at
                """
        try:
            row = await self.db.fetch_one(query, (discord_user_id, username, password, timezone))
            return Player(*row) if row else None
        except Exception as e:
            raise ValueError(f"Player creation failed: {e}")

    async def get_player_by_id(self, player_id: int) -> Optional[Player]:
        """READ: Get player by ID"""
        query = """
                SELECT id, \
                       discord_user_id, \
                       username, \
                       password, \
                       timezone, \
                       created_at
                FROM players
                WHERE id = %s
                """
        row = await self.db.fetch_one(query, (player_id,))
        return Player(*row) if row else None

    async def get_player_by_discord_id(self, discord_user_id: int) -> Optional[Player]:
        """READ: Get player by Discord user ID"""
        query = """
                SELECT id, \
                       discord_user_id, \
                       username, \
                       password, \
                       timezone, \
                       created_at
                FROM players
                WHERE discord_user_id = %s
                """
        row = await self.db.fetch_one(query, (discord_user_id,))
        return Player(*row) if row else None

    async def get_player_by_username(self, username: str) -> Optional[Player]:
        """READ: Get player by username"""
        query = """
                SELECT id, \
                       discord_user_id, \
                       username, \
                       password, \
                       timezone, \
                       created_at
                FROM players
                WHERE username = %s
                """
        row = await self.db.fetch_one(query, (username,))
        return Player(*row) if row else None

    async def list_players_in_league(self, league_id: int) -> List[Player]:
        """READ: Get all players in a league"""
        query = """
                SELECT p.id, p.discord_user_id, p.username, p.password, p.timezone, p.created_at
                FROM players p
                JOIN player_leagues pl ON pl.player_id = p.id
                WHERE pl.league_id = %s
                ORDER BY pl.joined_at
                """
        rows = await self.db.fetch_all(query, (league_id,))
        return [Player(*row) for row in rows]

    async def list_leagues_for_player(self, player_id: int) -> List[League]:
        """READ: Get all leagues a player belongs to"""
        query = """
                SELECT l.id, l.name, l.discord_guild_id, l.season_id, l.embed_color, l.created_at
                FROM leagues l
                JOIN player_leagues pl ON pl.league_id = l.id
                WHERE pl.player_id = %s
                ORDER BY pl.joined_at
                """
        rows = await self.db.fetch_all(query, (player_id,))
        return [League(*row) for row in rows]

    async def get_leagues_for_player_by_discord_id(self, discord_user_id: int) -> List[League]:
        """READ: Get all leagues a player belongs to by their Discord ID"""
        query = """
                SELECT l.id, l.name, l.discord_guild_id, l.season_id, l.embed_color, l.created_at
                FROM leagues l
                JOIN player_leagues pl ON pl.league_id = l.id
                JOIN players p ON p.id = pl.player_id
                WHERE p.discord_user_id = %s
                ORDER BY pl.joined_at
                """
        rows = await self.db.fetch_all(query, (discord_user_id,))
        return [League(*row) for row in rows]

    async def add_player_to_league(
            self,
            player_id: int,
            league_id: int,
            team_name: Optional[str],
            team_motto: Optional[str]
    ) -> Optional[PlayerLeague]:
        """CREATE: Add a player to a league with league-specific team info"""
        query = """
                INSERT INTO player_leagues (player_id, league_id, team_name, team_motto)
                VALUES (%s, %s, %s, %s) ON CONFLICT (player_id, league_id) DO NOTHING
                RETURNING player_id, league_id, team_name, team_motto, joined_at
                """
        try:
            row = await self.db.fetch_one(query, (player_id, league_id, team_name, team_motto))
            return PlayerLeague(*row) if row else None
        except Exception as e:
            raise ValueError(f"Failed to add player to league: {e}")

    async def remove_player_from_league(self, player_id: int, league_id: int) -> bool:
        """DELETE: Remove a player from a league"""
        query = "DELETE FROM player_leagues WHERE player_id = %s AND league_id = %s"
        await self.db.execute_query(query, (player_id, league_id))
        return True

    async def is_player_in_league(self, player_id: int, league_id: int) -> bool:
        """READ: Check if a player is in a specific league"""
        query = """
                SELECT EXISTS(
                    SELECT 1 FROM player_leagues 
                    WHERE player_id = %s AND league_id = %s
                )
                """
        row = await self.db.fetch_one(query, (player_id, league_id))
        return row[0] if row else False

    async def is_discord_user_in_league(self, discord_user_id: int, league_id: int) -> bool:
        """READ: Check if a Discord user is in a specific league"""
        query = """
                SELECT EXISTS(
                    SELECT 1 FROM player_leagues pl
                    JOIN players p ON p.id = pl.player_id
                    WHERE p.discord_user_id = %s AND pl.league_id = %s
                )
                """
        row = await self.db.fetch_one(query, (discord_user_id, league_id))
        return row[0] if row else False

    async def get_player_count_in_league(self, league_id: int) -> int:
        """READ: Get the number of players in a league"""
        query = """
                SELECT COUNT(*) 
                FROM player_leagues 
                WHERE league_id = %s
                """
        row = await self.db.fetch_one(query, (league_id,))
        return row[0] if row else 0

    async def get_league_count_for_player(self, player_id: int) -> int:
        """READ: Get the number of leagues a player is in"""
        query = """
                SELECT COUNT(*) 
                FROM player_leagues 
                WHERE player_id = %s
                """
        row = await self.db.fetch_one(query, (player_id,))
        return row[0] if row else 0

    async def update_team_name(self, player_id: int, league_id: int, team_name: str) -> bool:
        """UPDATE: Change player's team name for a specific league"""
        query = """
                UPDATE player_leagues
                SET team_name = %s
                WHERE player_id = %s \
                  AND league_id = %s
                """
        try:
            await self.db.execute_query(query, (team_name, player_id, league_id))
            return True
        except Exception:
            return False

    async def update_team_motto(self, player_id: int, league_id: int, team_motto: str) -> bool:
        """UPDATE: Change player's team motto for a specific league"""
        query = """
                UPDATE player_leagues
                SET team_motto = %s
                WHERE player_id = %s \
                  AND league_id = %s
                """
        await self.db.execute_query(query, (team_motto, player_id, league_id))
        return True

    async def get_player_league_info(self, player_id: int, league_id: int) -> Optional[PlayerLeague]:
        """READ: Get player's league-specific information"""
        query = """
                SELECT player_id, league_id, team_name, team_motto, joined_at
                FROM player_leagues
                WHERE player_id = %s \
                  AND league_id = %s
                """
        row = await self.db.fetch_one(query, (player_id, league_id))
        return PlayerLeague(*row) if row else None

    async def update_password(self, player_id: int, password_hash: str) -> bool:
        """UPDATE: Update player's password"""
        query = """
                UPDATE players
                SET password = %s
                WHERE id = %s
                """
        await self.db.execute_query(query, (password_hash, player_id))
        return True

    async def delete_player(self, player_id: int) -> bool:
        """DELETE: Remove a player (also removes all league associations due to CASCADE)"""
        query = "DELETE FROM players WHERE id = %s"
        await self.db.execute_query(query, (player_id,))
        return True


class DraftRepository:
    """Handles all database operations for drafts"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def create_draft(
            self,
            player_id: int,
            league_id: int,
            grand_prix_id: int,
            driver1_id: int,
            driver2_id: int,
            driver3_id: int,
            wildcard_id: int,
            constructor_id: int,
            is_auto_assigned: bool = False
    ) -> Optional[Draft]:
        """CREATE: Submit a draft for a specific league (upsert pattern)"""
        query = """
                INSERT INTO drafts (player_id, league_id, grand_prix_id, driver1_id, driver2_id, driver3_id, wildcard_id,
                                    constructor_id, is_auto_assigned, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()) 
                ON CONFLICT (player_id, league_id, grand_prix_id)
                DO UPDATE SET
                    driver1_id = EXCLUDED.driver1_id,
                    driver2_id = EXCLUDED.driver2_id,
                    driver3_id = EXCLUDED.driver3_id,
                    wildcard_id = EXCLUDED.wildcard_id,
                    constructor_id = EXCLUDED.constructor_id,
                    is_auto_assigned = EXCLUDED.is_auto_assigned,
                    updated_at = NOW()
                RETURNING id, player_id, league_id, grand_prix_id, driver1_id, driver2_id, driver3_id, wildcard_id, 
                          constructor_id, is_auto_assigned, created_at, updated_at
                """
        try:
            row = await self.db.fetch_one(query, (
                player_id, league_id, grand_prix_id, driver1_id, driver2_id, driver3_id,
                wildcard_id, constructor_id, is_auto_assigned
            ))
            return Draft(*row) if row else None
        except Exception as e:
            raise ValueError(f"Draft creation failed: {e}")

    async def get_draft(self, player_id: int, league_id: int, grand_prix_id: int) -> Optional[Draft]:
        """READ: Get a player's draft for a GP in a specific league"""
        query = """
                SELECT id, player_id, league_id, grand_prix_id, driver1_id, driver2_id, driver3_id,
                       wildcard_id, constructor_id, is_auto_assigned, created_at, updated_at
                FROM drafts
                WHERE player_id = %s AND league_id = %s AND grand_prix_id = %s
                """
        row = await self.db.fetch_one(query, (player_id, league_id, grand_prix_id))
        return Draft(*row) if row else None

    async def list_drafts_for_grand_prix_in_league(self, grand_prix_id: int, league_id: int) -> List[Draft]:
        """READ: Get all drafts for a Grand Prix in a specific league"""
        query = """
                SELECT id, player_id, league_id, grand_prix_id, driver1_id, driver2_id, driver3_id,
                       wildcard_id, constructor_id, is_auto_assigned, created_at, updated_at
                FROM drafts
                WHERE grand_prix_id = %s AND league_id = %s
                ORDER BY created_at
                """
        rows = await self.db.fetch_all(query, (grand_prix_id, league_id))
        return [Draft(*row) for row in rows]

    async def list_drafts_for_player_in_league(self, player_id: int, league_id: int) -> List[Draft]:
        """READ: Get all drafts for a player in a specific league"""
        query = """
                SELECT id, player_id, league_id, grand_prix_id, driver1_id, driver2_id, driver3_id,
                       wildcard_id, constructor_id, is_auto_assigned, created_at, updated_at
                FROM drafts
                WHERE player_id = %s AND league_id = %s
                ORDER BY grand_prix_id
                """
        rows = await self.db.fetch_all(query, (player_id, league_id))
        return [Draft(*row) for row in rows]

    async def get_all_drafts_for_player_for_gp(self, player_id: int, grand_prix_id: int) -> List[Draft]:
        """READ: Get all drafts for a player across all their leagues for a specific GP"""
        query = """
                SELECT d.id, d.player_id, d.league_id, d.grand_prix_id, d.driver1_id, d.driver2_id, d.driver3_id,
                       d.wildcard_id, d.constructor_id, d.is_auto_assigned, d.created_at, d.updated_at
                FROM drafts d
                JOIN player_leagues pl ON pl.league_id = d.league_id AND pl.player_id = d.player_id
                WHERE d.player_id = %s AND d.grand_prix_id = %s
                ORDER BY d.league_id
                """
        rows = await self.db.fetch_all(query, (player_id, grand_prix_id))
        return [Draft(*row) for row in rows]

    async def delete_draft(self, player_id: int, league_id: int, grand_prix_id: int) -> bool:
        """DELETE: Remove a draft"""
        query = "DELETE FROM drafts WHERE player_id = %s AND league_id = %s AND grand_prix_id = %s"
        await self.db.execute_query(query, (player_id, league_id, grand_prix_id))
        return True


class DriverExhaustionRepository:
    """Handles all database operations for driver exhaustion tracking"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def get_exhausted_drivers(
            self,
            player_id: int,
            league_id: int
    ) -> List[DriverExhaustion]:
        """READ: Get all exhausted drivers for a player in a league"""
        query = """
                SELECT id, player_id, league_id, driver_id, last_grand_prix_id, 
                       consecutive_uses, is_exhausted, created_at, updated_at
                FROM driver_exhaustion
                WHERE player_id = %s AND league_id = %s AND is_exhausted = TRUE
                ORDER BY driver_id
                """
        rows = await self.db.fetch_all(query, (player_id, league_id))
        return [DriverExhaustion(*row) for row in rows]

    async def get_driver_exhaustion_status(
            self,
            player_id: int,
            league_id: int,
            driver_id: int
    ) -> Optional[DriverExhaustion]:
        """READ: Get exhaustion status for a specific driver"""
        query = """
                SELECT id, player_id, league_id, driver_id, last_grand_prix_id, 
                       consecutive_uses, is_exhausted, created_at, updated_at
                FROM driver_exhaustion
                WHERE player_id = %s AND league_id = %s AND driver_id = %s
                """
        row = await self.db.fetch_one(query, (player_id, league_id, driver_id))
        return DriverExhaustion(*row) if row else None

    async def get_all_exhaustion_for_player(
            self,
            player_id: int,
            league_id: int
    ) -> List[DriverExhaustion]:
        """READ: Get all driver exhaustion records for a player in a league"""
        query = """
                SELECT id, player_id, league_id, driver_id, last_grand_prix_id, 
                       consecutive_uses, is_exhausted, created_at, updated_at
                FROM driver_exhaustion
                WHERE player_id = %s AND league_id = %s
                ORDER BY driver_id
                """
        rows = await self.db.fetch_all(query, (player_id, league_id))
        return [DriverExhaustion(*row) for row in rows]

    async def update_exhaustion_on_deadline(
            self,
            player_id: int,
            league_id: int,
            grand_prix_id: int
    ) -> None:
        """
        Update driver exhaustion status after a draft deadline passes.
        This should be called when points are calculated.

        Args:
            player_id: Player ID
            league_id: League ID
            grand_prix_id: Grand Prix ID (the one that just had its deadline pass)
        """
        query_get_draft = """
                          SELECT driver1_id, driver2_id, driver3_id, wildcard_id
                          FROM drafts
                          WHERE player_id = %s \
                            AND league_id = %s \
                            AND grand_prix_id = %s \
                          """
        draft_row = await self.db.fetch_one(query_get_draft, (player_id, league_id, grand_prix_id))

        if not draft_row:
            return

        driver_ids = [draft_row[0], draft_row[1], draft_row[2], draft_row[3]]

        # Get current GP round number
        query_gp = "SELECT round_number, season_id FROM grands_prix WHERE id = %s"
        gp_row = await self.db.fetch_one(query_gp, (grand_prix_id,))
        if not gp_row:
            return

        current_round = gp_row[0]
        season_id = gp_row[1]

        # Get previous GP for this league
        query_prev_gp = """
                        SELECT id, round_number
                        FROM grands_prix
                        WHERE season_id = %s \
                          AND round_number = %s \
                        """
        prev_gp_row = await self.db.fetch_one(query_prev_gp, (season_id, current_round - 1))

        if prev_gp_row:
            prev_gp_id = prev_gp_row[0]

            # Get previous draft
            prev_draft_row = await self.db.fetch_one(query_get_draft, (player_id, league_id, prev_gp_id))

            if prev_draft_row:
                prev_driver_ids = [prev_draft_row[0], prev_draft_row[1], prev_draft_row[2], prev_draft_row[3]]

                # Update exhaustion for each driver
                for driver_id in driver_ids:
                    if driver_id in prev_driver_ids:
                        # Driver used in consecutive races - increment/mark exhausted
                        query_upsert = """
                                       INSERT INTO driver_exhaustion
                                       (player_id, league_id, driver_id, last_grand_prix_id, consecutive_uses, \
                                        is_exhausted, updated_at)
                                       VALUES (%s, %s, %s, %s, 2, TRUE, NOW()) ON CONFLICT (player_id, league_id, driver_id)
                            DO \
                                       UPDATE SET
                                           consecutive_uses = driver_exhaustion.consecutive_uses + 1, \
                                           is_exhausted = TRUE, \
                                           last_grand_prix_id = EXCLUDED.last_grand_prix_id, \
                                           updated_at = NOW() \
                                       """
                        await self.db.execute_query(query_upsert, (player_id, league_id, driver_id, grand_prix_id))
                    else:
                        # Driver NOT used consecutively - reset
                        query_reset = """
                                      INSERT INTO driver_exhaustion
                                      (player_id, league_id, driver_id, last_grand_prix_id, consecutive_uses, \
                                       is_exhausted, updated_at)
                                      VALUES (%s, %s, %s, %s, 1, FALSE, NOW()) ON CONFLICT (player_id, league_id, driver_id)
                            DO \
                                      UPDATE SET
                                          consecutive_uses = 1, \
                                          is_exhausted = FALSE, \
                                          last_grand_prix_id = EXCLUDED.last_grand_prix_id, \
                                          updated_at = NOW() \
                                      """
                        await self.db.execute_query(query_reset, (player_id, league_id, driver_id, grand_prix_id))

                # Reset exhaustion for drivers NOT in current draft
                query_reset_unused = """
                                     UPDATE driver_exhaustion
                                     SET consecutive_uses = 0,
                                         is_exhausted     = FALSE,
                                         updated_at       = NOW()
                                     WHERE player_id = %s
                                       AND league_id = %s
                                       AND driver_id != ALL(%s)
                                       AND is_exhausted = TRUE \
                                     """
                await self.db.execute_query(query_reset_unused, (player_id, league_id, driver_ids))
        else:
            # First GP - initialize exhaustion
            for driver_id in driver_ids:
                query_init = """
                             INSERT INTO driver_exhaustion
                             (player_id, league_id, driver_id, last_grand_prix_id, consecutive_uses, is_exhausted, \
                              updated_at)
                             VALUES (%s, %s, %s, %s, 1, FALSE, NOW()) ON CONFLICT (player_id, league_id, driver_id)
                    DO \
                             UPDATE SET
                                 consecutive_uses = 1, \
                                 is_exhausted = FALSE, \
                                 last_grand_prix_id = EXCLUDED.last_grand_prix_id, \
                                 updated_at = NOW() \
                             """
                await self.db.execute_query(query_init, (player_id, league_id, driver_id, grand_prix_id))


class CounterpickRepository:
    """Handles all database operations for counterpicks"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def create_counterpick(
            self,
            grand_prix_id: int,
            league_id: int,
            picking_player_id: int,
            target_player_id: int,
            target_driver_id: int
    ) -> Optional[Counterpick]:
        """CREATE: Submit a counterpick (league-specific)"""
        query = """
                INSERT INTO counterpicks (grand_prix_id, league_id, picking_player_id, target_player_id, target_driver_id)
                VALUES (%s, %s, %s, %s, %s) 
                ON CONFLICT (grand_prix_id, league_id, picking_player_id)
                DO UPDATE SET
                    target_player_id = EXCLUDED.target_player_id,
                    target_driver_id = EXCLUDED.target_driver_id,
                    created_at = NOW()
                RETURNING id, grand_prix_id, league_id, picking_player_id, target_player_id, target_driver_id, created_at
                """
        try:
            row = await self.db.fetch_one(query, (grand_prix_id, league_id, picking_player_id, target_player_id, target_driver_id))
            return Counterpick(*row) if row else None
        except Exception as e:
            raise ValueError(f"Counterpick creation failed: {e}")

    async def get_counterpick(
            self,
            grand_prix_id: int,
            league_id: int,
            picking_player_id: int
    ) -> Optional[Counterpick]:
        """READ: Get a player's counterpick for a GP in a specific league"""
        query = """
                SELECT id, grand_prix_id, league_id, picking_player_id, target_player_id, target_driver_id, created_at
                FROM counterpicks
                WHERE grand_prix_id = %s 
                  AND league_id = %s
                  AND picking_player_id = %s
                """
        row = await self.db.fetch_one(query, (grand_prix_id, league_id, picking_player_id))
        return Counterpick(*row) if row else None

    async def list_counterpicks_for_grand_prix(
            self,
            grand_prix_id: int,
            league_id: int
    ) -> List[Counterpick]:
        """READ: Get all counterpicks for a Grand Prix in a specific league"""
        query = """
                SELECT id, grand_prix_id, league_id, picking_player_id, target_player_id, target_driver_id, created_at
                FROM counterpicks
                WHERE grand_prix_id = %s AND league_id = %s
                ORDER BY created_at
                """
        rows = await self.db.fetch_all(query, (grand_prix_id, league_id))
        return [Counterpick(*row) for row in rows]

    async def list_counterpicks_targeting_player(
            self,
            grand_prix_id: int,
            league_id: int,
            target_player_id: int
    ) -> List[Counterpick]:
        """READ: Get all counterpicks targeting a specific player in a league"""
        query = """
                SELECT id, grand_prix_id, league_id, picking_player_id, target_player_id, target_driver_id, created_at
                FROM counterpicks
                WHERE grand_prix_id = %s 
                  AND league_id = %s
                  AND target_player_id = %s
                """
        rows = await self.db.fetch_all(query, (grand_prix_id, league_id, target_player_id))
        return [Counterpick(*row) for row in rows]

    async def get_counterpicks_by_player_across_leagues(
            self,
            player_id: int,
            grand_prix_id: int
    ) -> List[Counterpick]:
        """READ: Get all counterpicks made by a player across all their leagues for a GP"""
        query = """
                SELECT c.id, c.grand_prix_id, c.league_id, c.picking_player_id, 
                       c.target_player_id, c.target_driver_id, c.created_at
                FROM counterpicks c
                JOIN player_leagues pl ON pl.league_id = c.league_id
                WHERE c.picking_player_id = %s 
                  AND c.grand_prix_id = %s
                  AND pl.player_id = %s
                ORDER BY c.created_at
                """
        rows = await self.db.fetch_all(query, (player_id, grand_prix_id, player_id))
        return [Counterpick(*row) for row in rows]

    async def get_counterpicks_for_player_in_league(
            self,
            player_id: int,
            league_id: int
    ) -> List[Counterpick]:
        """READ: Get all counterpicks for a player in a specific league"""
        query = """
                SELECT id, grand_prix_id, league_id, picking_player_id, target_player_id, target_driver_id, created_at
                FROM counterpicks
                WHERE picking_player_id = %s AND league_id = %s
        """
        rows = await self.db.fetch_all(query, (player_id, league_id))
        return [Counterpick(*row) for row in rows]

    async def get_remaining_counterpicks(
            self,
            player_id: int,
            league_id: int,
            season_id: int
    ) -> int:
        """Get the number of remaining counterpicks for a player in a league this season"""
        query = """
                SELECT l.counterpick_limit, COALESCE(cu.used_count, 0) as used_count
                FROM leagues l
                         LEFT JOIN counterpick_usage cu ON cu.league_id = l.id
                    AND cu.player_id = %s
                    AND cu.season_id = %s
                WHERE l.id = %s
                """
        row = await self.db.fetch_one(query, (player_id, season_id, league_id))
        if row:
            limit, used = row
            return max(0, limit - used)
        return 0

    async def get_counterpick_usage(
            self,
            player_id: int,
            league_id: int,
            season_id: int
    ) -> Optional[CounterpickUsage]:
        """Get counterpick usage stats for a player in a league this season"""
        query = """
                SELECT player_id, league_id, season_id, used_count
                FROM counterpick_usage
                WHERE player_id = %s \
                  AND league_id = %s \
                  AND season_id = %s
                """
        row = await self.db.fetch_one(query, (player_id, league_id, season_id))
        return CounterpickUsage(*row) if row else None

    async def get_target_counterpick_count(
            self,
            target_player_id: int,
            grand_prix_id: int,
            league_id: int
    ) -> int:
        """Get the number of counterpicks already targeting a player for a specific GP"""
        query = """
                SELECT COUNT(*)
                FROM counterpicks
                WHERE target_player_id = %s
                  AND grand_prix_id = %s
                  AND league_id = %s
                """
        row = await self.db.fetch_one(query, (target_player_id, grand_prix_id, league_id))
        return row[0] if row else 0

    async def can_counterpick(
            self,
            picking_player_id: int,
            target_player_id: int,
            grand_prix_id: int,
            league_id: int,
            season_id: int
    ) -> tuple[bool, str]:
        """
        Check if a player can make a counterpick

        Returns:
            (can_counterpick: bool, reason: str) - True if allowed, False with reason if not
        """
        # Check if player has counterpicks remaining
        remaining = await self.get_remaining_counterpicks(picking_player_id, league_id, season_id)

        # Check if this is an update to an existing counterpick for this GP
        existing = await self.get_counterpick(grand_prix_id, league_id, picking_player_id)

        # If no existing counterpick for this GP and no remaining counterpicks, reject
        if not existing and remaining <= 0:
            return False, f"You have used all your counterpicks for this season"

        # Check if target already has 2 counterpicks
        target_count = await self.get_target_counterpick_count(target_player_id, grand_prix_id, league_id)

        # If updating existing counterpick to different target, don't count old one
        if existing and existing.target_player_id != target_player_id:
            if target_count >= 2:
                return False, f"Target player already has the maximum of 2 counterpicks against them for this Grand Prix"
        elif not existing and target_count >= 2:
            return False, f"Target player already has the maximum of 2 counterpicks against them for this Grand Prix"

        return True, "Counterpick allowed"

    async def delete_counterpick(
            self,
            grand_prix_id: int,
            league_id: int,
            picking_player_id: int
    ) -> bool:
        """DELETE: Remove a counterpick"""
        query = "DELETE FROM counterpicks WHERE grand_prix_id = %s AND league_id = %s AND picking_player_id = %s"
        await self.db.execute_query(query, (grand_prix_id, league_id, picking_player_id))
        return True


class RaceResultRepository:
    """Handles all database operations for race results"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def create_race_result(
            self,
            grand_prix_id: int,
            session_type: str,
            driver_id: int,
            position: int
    ) -> Optional[RaceResult]:
        """CREATE: Add a race result"""
        query = """
                INSERT INTO race_results (grand_prix_id, session_type, driver_id, position)
                VALUES (%s, %s, %s, %s) 
                ON CONFLICT (grand_prix_id, session_type, driver_id)
                DO UPDATE SET position = EXCLUDED.position
                RETURNING id, grand_prix_id, session_type, driver_id, position
                """
        try:
            row = await self.db.fetch_one(query, (grand_prix_id, session_type, driver_id, position))
            return RaceResult(*row) if row else None
        except Exception as e:
            raise ValueError(f"Race result creation failed: {e}")

    async def get_race_results_by_session(self, grand_prix_id: int, session_type: str) -> List[RaceResult]:
        """READ: Get all results for a session"""
        query = """
                SELECT id, grand_prix_id, session_type, driver_id, position
                FROM race_results
                WHERE grand_prix_id = %s AND session_type = %s
                ORDER BY position
                """
        rows = await self.db.fetch_all(query, (grand_prix_id, session_type))
        return [RaceResult(*row) for row in rows]

    async def get_all_race_results_for_gp(self, grand_prix_id: int) -> List[RaceResult]:
        """READ: Get all results for a Grand Prix (all sessions)"""
        query = """
                SELECT id, grand_prix_id, session_type, driver_id, position
                FROM race_results
                WHERE grand_prix_id = %s
                ORDER BY session_type, position
                """
        rows = await self.db.fetch_all(query, (grand_prix_id,))
        return [RaceResult(*row) for row in rows]

    async def delete_race_results_for_session(self, grand_prix_id: int, session_type: str) -> bool:
        """DELETE: Remove all results for a session"""
        query = "DELETE FROM race_results WHERE grand_prix_id = %s AND session_type = %s"
        await self.db.execute_query(query, (grand_prix_id, session_type))
        return True


class PlayerRoundScoreRepository:
    """Handles all database operations for player round scores"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def create_or_update_score(
            self,
            player_id: int,
            league_id: int,
            grand_prix_id: int,
            total_points: int,
            breakdown_json: Dict[str, Any]
    ) -> Optional[PlayerRoundScore]:
        """CREATE/UPDATE: Store player's score for a GP in a specific league"""
        query = """
                INSERT INTO player_round_scores (player_id, league_id, grand_prix_id, total_points, breakdown_json, calculated_at)
                VALUES (%s, %s, %s, %s, %s, NOW()) 
                ON CONFLICT (player_id, league_id, grand_prix_id)
                DO UPDATE SET
                    total_points = EXCLUDED.total_points,
                    breakdown_json = EXCLUDED.breakdown_json,
                    calculated_at = NOW()
                RETURNING id, player_id, league_id, grand_prix_id, total_points, breakdown_json, calculated_at
                """
        try:
            import json
            breakdown_str = json.dumps(breakdown_json)
            row = await self.db.fetch_one(query, (player_id, league_id, grand_prix_id, total_points, breakdown_str))
            if row:
                return PlayerRoundScore(
                    id=row[0],
                    player_id=row[1],
                    league_id=row[2],
                    grand_prix_id=row[3],
                    total_points=row[4],
                    breakdown_json=row[5] if isinstance(row[5], dict) else json.loads(row[5]),
                    calculated_at=row[6]
                )
            return None
        except Exception as e:
            raise ValueError(f"Score creation failed: {e}")

    async def get_score(self, player_id: int, league_id: int, grand_prix_id: int) -> Optional[PlayerRoundScore]:
        """READ: Get a player's score for a GP in a specific league"""
        query = """
                SELECT id, player_id, league_id, grand_prix_id, total_points, breakdown_json, calculated_at
                FROM player_round_scores
                WHERE player_id = %s AND league_id = %s AND grand_prix_id = %s
                """
        row = await self.db.fetch_one(query, (player_id, league_id, grand_prix_id))
        if row:
            import json
            return PlayerRoundScore(
                id=row[0],
                player_id=row[1],
                league_id=row[2],
                grand_prix_id=row[3],
                total_points=row[4],
                breakdown_json=row[5] if isinstance(row[5], dict) else json.loads(row[5]),
                calculated_at=row[6]
            )
        return None

    async def list_scores_for_player_in_league(self, player_id: int, league_id: int) -> List[PlayerRoundScore]:
        """READ: Get all scores for a player in a specific league"""
        query = """
                SELECT prs.id, prs.player_id, prs.league_id, prs.grand_prix_id, prs.total_points,
                       prs.breakdown_json, prs.calculated_at
                FROM player_round_scores prs
                JOIN grands_prix gp ON gp.id = prs.grand_prix_id
                WHERE prs.player_id = %s AND prs.league_id = %s
                ORDER BY gp.round_number
                """
        rows = await self.db.fetch_all(query, (player_id, league_id))
        import json
        return [
            PlayerRoundScore(
                id=row[0],
                player_id=row[1],
                league_id=row[2],
                grand_prix_id=row[3],
                total_points=row[4],
                breakdown_json=row[5] if isinstance(row[5], dict) else json.loads(row[5]),
                calculated_at=row[6]
            )
            for row in rows
        ]

    async def list_scores_for_grand_prix_in_league(self, grand_prix_id: int, league_id: int) -> List[PlayerRoundScore]:
        """READ: Get all scores for a Grand Prix in a specific league"""
        query = """
                SELECT id, player_id, league_id, grand_prix_id, total_points, breakdown_json, calculated_at
                FROM player_round_scores
                WHERE grand_prix_id = %s AND league_id = %s
                ORDER BY total_points DESC
                """
        rows = await self.db.fetch_all(query, (grand_prix_id, league_id))
        import json
        return [
            PlayerRoundScore(
                id=row[0],
                player_id=row[1],
                league_id=row[2],
                grand_prix_id=row[3],
                total_points=row[4],
                breakdown_json=row[5] if isinstance(row[5], dict) else json.loads(row[5]),
                calculated_at=row[6]
            )
            for row in rows
        ]

    async def get_all_scores_for_player_for_gp(self, player_id: int, grand_prix_id: int) -> List[PlayerRoundScore]:
        """READ: Get all scores for a player across all their leagues for a specific GP"""
        query = """
                SELECT prs.id, prs.player_id, prs.league_id, prs.grand_prix_id, prs.total_points,
                       prs.breakdown_json, prs.calculated_at
                FROM player_round_scores prs
                JOIN player_leagues pl ON pl.league_id = prs.league_id AND pl.player_id = prs.player_id
                WHERE prs.player_id = %s AND prs.grand_prix_id = %s
                ORDER BY prs.league_id
                """
        rows = await self.db.fetch_all(query, (player_id, grand_prix_id))
        import json
        return [
            PlayerRoundScore(
                id=row[0],
                player_id=row[1],
                league_id=row[2],
                grand_prix_id=row[3],
                total_points=row[4],
                breakdown_json=row[5] if isinstance(row[5], dict) else json.loads(row[5]),
                calculated_at=row[6]
            )
            for row in rows
        ]

    async def delete_score(self, player_id: int, league_id: int, grand_prix_id: int) -> bool:
        """DELETE: Remove a player's score"""
        query = "DELETE FROM player_round_scores WHERE player_id = %s AND league_id = %s AND grand_prix_id = %s"
        await self.db.execute_query(query, (player_id, league_id, grand_prix_id))
        return True

    async def get_player_season_stats(self, player_id: int, league_id: int) -> Optional[Dict[str, Any]]:
        """READ: Get player's season statistics for a league"""
        query = """
                SELECT COUNT(DISTINCT prs.grand_prix_id)  AS rounds_participated,
                       COALESCE(SUM(prs.total_points), 0) AS total_points,
                       COALESCE(MAX(prs.total_points), 0) AS best_round_score,
                       COALESCE(MIN(prs.total_points), 0) AS worst_round_score,
                       COALESCE(AVG(prs.total_points), 0) AS avg_points_per_round
                FROM player_round_scores prs
                WHERE prs.player_id = %s \
                  AND prs.league_id = %s
                """
        row = await self.db.fetch_one(query, (player_id, league_id))
        if row and row[0] > 0:  # Only return if player has participated in at least one round
            return {
                "rounds_participated": row[0],
                "total_points": row[1],
                "best_round_score": row[2],
                "worst_round_score": row[3],
                "avg_points_per_round": round(float(row[4]), 2)
            }
        return None


class ScoringRuleRepository:
    """Handles all database operations for scoring rules"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def create_or_update_rule(
            self,
            season_id: int,
            rule_key: str,
            rule_value: Any
    ) -> Optional[ScoringRule]:
        """CREATE/UPDATE: Store a scoring rule"""
        query = """
                INSERT INTO scoring_rules (season_id, rule_key, rule_value)
                VALUES (%s, %s, %s) 
                ON CONFLICT (season_id, rule_key)
                DO UPDATE SET rule_value = EXCLUDED.rule_value
                RETURNING id, season_id, rule_key, rule_value
                """
        try:
            import json
            rule_value_str = json.dumps(rule_value)
            row = await self.db.fetch_one(query, (season_id, rule_key, rule_value_str))
            if row:
                return ScoringRule(
                    id=row[0],
                    season_id=row[1],
                    rule_key=row[2],
                    rule_value=row[3] if isinstance(row[3], (list, dict, int, str)) else json.loads(row[3])
                )
            return None
        except Exception as e:
            raise ValueError(f"Scoring rule creation failed: {e}")

    async def get_rule(self, season_id: int, rule_key: str) -> Optional[ScoringRule]:
        """READ: Get a specific scoring rule"""
        query = """
                SELECT id, season_id, rule_key, rule_value
                FROM scoring_rules
                WHERE season_id = %s AND rule_key = %s
                """
        row = await self.db.fetch_one(query, (season_id, rule_key))
        if row:
            import json
            return ScoringRule(
                id=row[0],
                season_id=row[1],
                rule_key=row[2],
                rule_value=row[3] if isinstance(row[3], (list, dict, int, str)) else json.loads(row[3])
            )
        return None

    async def list_rules_for_season(self, season_id: int) -> List[ScoringRule]:
        """READ: Get all scoring rules for a season"""
        query = """
                SELECT id, season_id, rule_key, rule_value
                FROM scoring_rules
                WHERE season_id = %s
                ORDER BY rule_key
                """
        rows = await self.db.fetch_all(query, (season_id,))
        import json
        return [
            ScoringRule(
                id=row[0],
                season_id=row[1],
                rule_key=row[2],
                rule_value=row[3] if isinstance(row[3], (list, dict, int, str)) else json.loads(row[3])
            )
            for row in rows
        ]

    async def delete_rule(self, season_id: int, rule_key: str) -> bool:
        """DELETE: Remove a scoring rule"""
        query = "DELETE FROM scoring_rules WHERE season_id = %s AND rule_key = %s"
        await self.db.execute_query(query, (season_id, rule_key))
        return True


class LeaderboardRepository:
    """Handles leaderboard queries"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def get_league_leaderboard(self, league_id: int) -> List[Dict[str, Any]]:
        """READ: Get full season leaderboard for a league"""
        query = """
                SELECT p.id AS player_id,
                       p.username,
                       p.team_name,
                       COALESCE(SUM(prs.total_points), 0) AS total_points,
                       COUNT(DISTINCT prs.grand_prix_id) AS rounds_played
                FROM players p
                JOIN player_leagues pl ON pl.player_id = p.id
                LEFT JOIN player_round_scores prs ON prs.player_id = p.id AND prs.league_id = pl.league_id
                WHERE pl.league_id = %s
                GROUP BY p.id, p.username, p.team_name
                ORDER BY total_points DESC, rounds_played DESC, p.username
                """
        rows = await self.db.fetch_all(query, (league_id,))
        return [
            {
                "player_id": row[0],
                "username": row[1],
                "team_name": row[2],
                "total_points": row[3],
                "rounds_played": row[4]
            }
            for row in rows
        ]

    async def get_grand_prix_leaderboard(
            self,
            grand_prix_id: int,
            league_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """READ: Get leaderboard for a specific Grand Prix, optionally filtered by league"""
        if league_id:
            query = """
                    SELECT p.id AS player_id,
                           p.username,
                           p.team_name,
                           prs.total_points,
                           prs.breakdown_json
                    FROM player_round_scores prs
                    JOIN players p ON p.id = prs.player_id
                    WHERE prs.grand_prix_id = %s AND prs.league_id = %s
                    ORDER BY prs.total_points DESC, p.username
                    """
            rows = await self.db.fetch_all(query, (grand_prix_id, league_id))
        else:
            query = """
                    SELECT p.id AS player_id,
                           p.username,
                           p.team_name,
                           prs.total_points,
                           prs.breakdown_json
                    FROM player_round_scores prs
                    JOIN players p ON p.id = prs.player_id
                    WHERE prs.grand_prix_id = %s
                    ORDER BY prs.total_points DESC, p.username
                    """
            rows = await self.db.fetch_all(query, (grand_prix_id,))

        import json
        return [
            {
                "player_id": row[0],
                "username": row[1],
                "team_name": row[2],
                "total_points": row[3],
                "breakdown": row[4] if isinstance(row[4], dict) else json.loads(row[4])
            }
            for row in rows
        ]

    async def get_player_league_stats(
            self,
            player_id: int,
            league_id: int
    ) -> Optional[Dict[str, Any]]:
        """READ: Get a player's statistics for a specific league"""
        query = """
                SELECT COUNT(DISTINCT prs.grand_prix_id) AS rounds_participated,
                       COALESCE(SUM(prs.total_points), 0) AS total_points,
                       COALESCE(AVG(prs.total_points), 0) AS avg_points_per_round,
                       COALESCE(MAX(prs.total_points), 0) AS best_round_score,
                       COALESCE(MIN(prs.total_points), 0) AS worst_round_score,
                       (SELECT COUNT(*)
                        FROM grands_prix gp
                        JOIN leagues l ON l.season_id = gp.season_id
                        WHERE l.id = %s AND gp.is_completed = TRUE) AS total_completed_rounds
                FROM player_round_scores prs
                JOIN grands_prix gp ON gp.id = prs.grand_prix_id
                WHERE prs.player_id = %s AND prs.league_id = %s
                """
        row = await self.db.fetch_one(query, (league_id, player_id, league_id))
        if row:
            return {
                "rounds_participated": row[0],
                "total_points": row[1],
                "avg_points_per_round": float(row[2]),
                "best_round_score": row[3],
                "worst_round_score": row[4],
                "total_completed_rounds": row[5]
            }
        return None

    async def get_league_standings_with_rankings(self, league_id: int) -> List[Dict[str, Any]]:
        """READ: Get league standings with rank positions and gaps"""
        query = """
                WITH ranked_players AS (
                    SELECT p.id AS player_id,
                           p.username,
                           p.team_name,
                           COALESCE(SUM(prs.total_points), 0) AS total_points,
                           COUNT(DISTINCT prs.grand_prix_id) AS rounds_played,
                           RANK() OVER (ORDER BY COALESCE(SUM(prs.total_points), 0) DESC) AS rank
                    FROM players p
                    JOIN player_leagues pl ON pl.player_id = p.id
                    LEFT JOIN player_round_scores prs ON prs.player_id = p.id AND prs.league_id = pl.league_id
                    WHERE pl.league_id = %s
                    GROUP BY p.id, p.username, p.team_name
                )
                SELECT rp.*,
                       rp.total_points - LEAD(rp.total_points, 1, 0) OVER (ORDER BY rp.total_points DESC) AS gap_to_next
                FROM ranked_players rp
                ORDER BY rp.rank
                """
        rows = await self.db.fetch_all(query, (league_id,))
        return [
            {
                "player_id": row[0],
                "username": row[1],
                "team_name": row[2],
                "total_points": row[3],
                "rounds_played": row[4],
                "rank": row[5],
                "gap_to_next": row[6]
            }
            for row in rows
        ]


class StatisticsRepository:
    """Handles all statistics queries"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def get_most_drafted_driver_per_league(
            self,
            season_id: int,
            league_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get the most drafted driver in a specific league for a season"""
        query = """
                SELECT driver_id, code, first_name, last_name, 
                       total_times_drafted, unique_players_drafted_by
                FROM v_driver_draft_stats
                WHERE season_id = %s AND league_id = %s
                ORDER BY total_times_drafted DESC, unique_players_drafted_by DESC
                LIMIT 1
                """
        row = await self.db.fetch_one(query, (season_id, league_id))
        if row:
            return {
                "driver_id": row[0],
                "code": row[1],
                "first_name": row[2],
                "last_name": row[3],
                "total_times_drafted": row[4],
                "unique_players_drafted_by": row[5]
            }
        return None

    async def get_least_drafted_driver_per_league(
            self,
            season_id: int,
            league_id: int,
            min_drafts: int = 1
    ) -> Optional[Dict[str, Any]]:
        """Get the least drafted driver in a specific league for a season (excluding undrafted)"""
        query = """
                SELECT driver_id, code, first_name, last_name, 
                       total_times_drafted, unique_players_drafted_by
                FROM v_driver_draft_stats
                WHERE season_id = %s AND league_id = %s AND total_times_drafted >= %s
                ORDER BY total_times_drafted ASC, unique_players_drafted_by ASC
                LIMIT 1
                """
        row = await self.db.fetch_one(query, (season_id, league_id, min_drafts))
        if row:
            return {
                "driver_id": row[0],
                "code": row[1],
                "first_name": row[2],
                "last_name": row[3],
                "total_times_drafted": row[4],
                "unique_players_drafted_by": row[5]
            }
        return None

    async def get_most_drafted_driver_across_all_leagues(
            self,
            season_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get the most drafted driver across all leagues in a season"""
        query = """
                SELECT driver_id, code, first_name, last_name, 
                       total_times_drafted, unique_players_drafted_by, leagues_drafted_in
                FROM v_driver_draft_stats_season
                WHERE season_id = %s
                ORDER BY total_times_drafted DESC, unique_players_drafted_by DESC
                LIMIT 1
                """
        row = await self.db.fetch_one(query, (season_id,))
        if row:
            return {
                "driver_id": row[0],
                "code": row[1],
                "first_name": row[2],
                "last_name": row[3],
                "total_times_drafted": row[4],
                "unique_players_drafted_by": row[5],
                "leagues_drafted_in": row[6]
            }
        return None

    async def get_least_drafted_driver_across_all_leagues(
            self,
            season_id: int,
            min_drafts: int = 1
    ) -> Optional[Dict[str, Any]]:
        """Get the least drafted driver across all leagues in a season"""
        query = """
                SELECT driver_id, code, first_name, last_name, 
                       total_times_drafted, unique_players_drafted_by, leagues_drafted_in
                FROM v_driver_draft_stats_season
                WHERE season_id = %s AND total_times_drafted >= %s
                ORDER BY total_times_drafted ASC, unique_players_drafted_by ASC
                LIMIT 1
                """
        row = await self.db.fetch_one(query, (season_id, min_drafts))
        if row:
            return {
                "driver_id": row[0],
                "code": row[1],
                "first_name": row[2],
                "last_name": row[3],
                "total_times_drafted": row[4],
                "unique_players_drafted_by": row[5],
                "leagues_drafted_in": row[6]
            }
        return None

    async def get_driver_draft_count_by_player(
            self,
            player_id: int,
            league_id: int,
            season_id: int
    ) -> List[Dict[str, Any]]:
        """Get how many times each driver was drafted by a specific player in a league"""
        query = """
                SELECT 
                    d.id AS driver_id,
                    d.code,
                    d.first_name,
                    d.last_name,
                    COUNT(DISTINCT CASE 
                        WHEN dr.driver1_id = d.id OR dr.driver2_id = d.id OR dr.driver3_id = d.id OR dr.wildcard_id = d.id
                        THEN dr.grand_prix_id 
                    END) AS times_drafted,
                    COUNT(DISTINCT CASE 
                        WHEN dr.driver1_id = d.id OR dr.driver2_id = d.id OR dr.driver3_id = d.id
                        THEN dr.grand_prix_id 
                    END) AS times_drafted_main,
                    COUNT(DISTINCT CASE 
                        WHEN dr.wildcard_id = d.id
                        THEN dr.grand_prix_id 
                    END) AS times_drafted_bogey
                FROM drivers d
                LEFT JOIN drafts dr ON (
                    (dr.driver1_id = d.id OR dr.driver2_id = d.id OR dr.driver3_id = d.id OR dr.wildcard_id = d.id)
                    AND dr.player_id = %s
                    AND dr.league_id = %s
                )
                WHERE d.season_id = %s
                GROUP BY d.id, d.code, d.first_name, d.last_name
                HAVING COUNT(DISTINCT CASE 
                    WHEN dr.driver1_id = d.id OR dr.driver2_id = d.id OR dr.driver3_id = d.id OR dr.wildcard_id = d.id
                    THEN dr.grand_prix_id 
                END) > 0
                ORDER BY times_drafted DESC, d.last_name
                """
        rows = await self.db.fetch_all(query, (player_id, league_id, season_id))
        return [
            {
                "driver_id": row[0],
                "code": row[1],
                "first_name": row[2],
                "last_name": row[3],
                "times_drafted": row[4],
                "times_drafted_main": row[5],
                "times_drafted_bogey": row[6]
            }
            for row in rows
        ]

    async def get_driver_points_for_player(
            self,
            player_id: int,
            league_id: int,
            season_id: int
    ) -> List[Dict[str, Any]]:
        """Get total points each driver scored for a player in a league over the season"""
        query = """
                SELECT 
                    d.id AS driver_id,
                    d.code,
                    d.first_name,
                    d.last_name,
                    COUNT(DISTINCT dr.grand_prix_id) AS times_drafted,
                    COALESCE(SUM(
                        CASE 
                            WHEN prs.breakdown_json ? d.code 
                            THEN (prs.breakdown_json->d.code->>'points')::int
                            ELSE 0
                        END
                    ), 0) AS total_points_scored
                FROM drivers d
                JOIN drafts dr ON (
                    (dr.driver1_id = d.id OR dr.driver2_id = d.id OR dr.driver3_id = d.id OR dr.wildcard_id = d.id)
                    AND dr.player_id = %s
                    AND dr.league_id = %s
                )
                JOIN grands_prix gp ON gp.id = dr.grand_prix_id AND gp.is_completed = TRUE
                LEFT JOIN player_round_scores prs ON (
                    prs.player_id = dr.player_id 
                    AND prs.league_id = dr.league_id 
                    AND prs.grand_prix_id = dr.grand_prix_id
                )
                WHERE d.season_id = %s
                GROUP BY d.id, d.code, d.first_name, d.last_name
                ORDER BY total_points_scored DESC, times_drafted DESC
                """
        rows = await self.db.fetch_all(query, (player_id, league_id, season_id))
        return [
            {
                "driver_id": row[0],
                "code": row[1],
                "first_name": row[2],
                "last_name": row[3],
                "times_drafted": row[4],
                "total_points_scored": row[5]
            }
            for row in rows
        ]

    async def get_all_driver_draft_stats_for_league(
            self,
            league_id: int,
            season_id: int
    ) -> List[Dict[str, Any]]:
        """Get draft statistics for all drivers in a league"""
        query = """
                SELECT driver_id, code, first_name, last_name,
                       times_drafted_as_main, times_drafted_as_bogey,
                       total_times_drafted, unique_players_drafted_by
                FROM v_driver_draft_stats
                WHERE league_id = %s AND season_id = %s
                ORDER BY total_times_drafted DESC
                """
        rows = await self.db.fetch_all(query, (league_id, season_id))
        return [
            {
                "driver_id": row[0],
                "code": row[1],
                "first_name": row[2],
                "last_name": row[3],
                "times_drafted_as_main": row[4],
                "times_drafted_as_bogey": row[5],
                "total_times_drafted": row[6],
                "unique_players_drafted_by": row[7]
            }
            for row in rows
        ]