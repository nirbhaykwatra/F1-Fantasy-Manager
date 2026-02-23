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


@dataclass
class Player:
    """Represents a player in the fantasy league"""
    id: int
    discord_user_id: Optional[int]
    username: str
    password: Optional[str]
    team_name: Optional[str]
    team_motto: Optional[str]
    timezone: str
    created_at: datetime


@dataclass
class PlayerLeague:
    """Represents a player's membership in a league"""
    player_id: int
    league_id: int
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
            is_active: bool = True
    ) -> Optional[Driver]:
        """CREATE: Add a new driver"""
        query = """
                INSERT INTO drivers (season_id, code, number, first_name, last_name, constructor_id, ergast_id, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) 
                RETURNING id, season_id, code, number, first_name, last_name, constructor_id, ergast_id, is_active
                """
        try:
            row = await self.db.fetch_one(query, (season_id, code, number, first_name, last_name, constructor_id, ergast_id,
                                                  is_active))
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
                       is_active
                FROM drivers
                WHERE id = %s
                """
        row = await self.db.fetch_one(query, (driver_id,))
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
                       is_active
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
                       is_active
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
            embed_color: int = 0xE8272A
    ) -> Optional[League]:
        """CREATE: Create a new league"""
        query = """
                INSERT INTO leagues (name, discord_guild_id, season_id, embed_color)
                VALUES (%s, %s, %s, %s) RETURNING id, name, discord_guild_id, season_id, embed_color, created_at
                """
        try:
            row = await self.db.fetch_one(query, (name, discord_guild_id, season_id, embed_color))
            return League(*row) if row else None
        except Exception as e:
            raise ValueError(f"League creation failed: {e}")

    async def get_league_by_id(self, league_id: int) -> Optional[League]:
        """READ: Get league by ID"""
        query = """
                SELECT id, name, discord_guild_id, season_id, embed_color, created_at
                FROM leagues
                WHERE id = %s
                """
        row = await self.db.fetch_one(query, (league_id,))
        return League(*row) if row else None

    async def get_league_by_discord_guild(self, discord_guild_id: int) -> Optional[League]:
        """READ: Get league by Discord guild ID"""
        query = """
                SELECT id, name, discord_guild_id, season_id, embed_color, created_at
                FROM leagues
                WHERE discord_guild_id = %s
                """
        row = await self.db.fetch_one(query, (discord_guild_id,))
        return League(*row) if row else None

    async def get_leagues_by_discord_guild(self, discord_guild_id: int) -> List[League]:
        """READ: Get all leagues by Discord guild ID"""
        query = """
                SELECT id, name, discord_guild_id, season_id, embed_color, created_at
                FROM leagues
                WHERE discord_guild_id = %s
                ORDER BY created_at
                """
        rows = await self.db.fetch_all(query, (discord_guild_id,))
        return [League(*row) for row in rows]

    async def list_leagues_by_season(self, season_id: int) -> List[League]:
        """READ: Get all leagues for a season"""
        query = """
                SELECT id, name, discord_guild_id, season_id, embed_color, created_at
                FROM leagues
                WHERE season_id = %s
                ORDER BY created_at
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
            team_name: Optional[str] = None,
            team_motto: Optional[str] = None,
            timezone: str = "UTC"
    ) -> Optional[Player]:
        """CREATE: Register a new player (without league association)"""
        query = """
                INSERT INTO players (discord_user_id, username, password, team_name, team_motto, timezone)
                VALUES (%s, %s, %s, %s, %s, %s) 
                RETURNING id, discord_user_id, username, password, team_name, team_motto, timezone, created_at
                """
        try:
            row = await self.db.fetch_one(query, (discord_user_id, username, password, team_name, team_motto,
                                                  timezone))
            return Player(*row) if row else None
        except Exception as e:
            raise ValueError(f"Player creation failed: {e}")

    async def get_player_by_id(self, player_id: int) -> Optional[Player]:
        """READ: Get player by ID"""
        query = """
                SELECT id, discord_user_id, username, password, team_name, team_motto, timezone, created_at
                FROM players
                WHERE id = %s
                """
        row = await self.db.fetch_one(query, (player_id,))
        return Player(*row) if row else None

    async def get_player_by_discord_id(self, discord_user_id: int) -> Optional[Player]:
        """READ: Get player by Discord user ID"""
        query = """
                SELECT id, discord_user_id, username, password, team_name, team_motto, timezone, created_at
                FROM players
                WHERE discord_user_id = %s
                """
        row = await self.db.fetch_one(query, (discord_user_id,))
        return Player(*row) if row else None

    async def get_player_by_username(self, username: str) -> Optional[Player]:
        """READ: Get player by username"""
        query = """
                SELECT id, discord_user_id, username, password, team_name, team_motto, timezone, created_at
                FROM players
                WHERE username = %s
                """
        row = await self.db.fetch_one(query, (username,))
        return Player(*row) if row else None

    async def list_players_in_league(self, league_id: int) -> List[Player]:
        """READ: Get all players in a league"""
        query = """
                SELECT p.id, p.discord_user_id, p.username, p.password, p.team_name, p.team_motto, p.timezone, p.created_at
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

    async def add_player_to_league(self, player_id: int, league_id: int) -> Optional[PlayerLeague]:
        """CREATE: Add a player to a league"""
        query = """
                INSERT INTO player_leagues (player_id, league_id)
                VALUES (%s, %s)
                ON CONFLICT (player_id, league_id) DO NOTHING
                RETURNING player_id, league_id, joined_at
                """
        try:
            row = await self.db.fetch_one(query, (player_id, league_id))
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

    async def update_team_name(self, player_id: int, team_name: str) -> bool:
        """UPDATE: Change player's team name"""
        query = """
                UPDATE players
                SET team_name = %s
                WHERE id = %s
                """
        try:
            await self.db.execute_query(query, (team_name, player_id))
            return True
        except Exception:
            return False

    async def update_team_motto(self, player_id: int, team_motto: str) -> bool:
        """UPDATE: Change player's team motto"""
        query = """
                UPDATE players
                SET team_motto = %s
                WHERE id = %s
                """
        await self.db.execute_query(query, (team_motto, player_id))
        return True

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