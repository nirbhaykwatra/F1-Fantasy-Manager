import pytest
import pytest_asyncio
from datetime import datetime
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from f1bot.services.models import (
    SeasonRepository, ConstructorRepository, DriverRepository, GrandPrixRepository,
    LeagueRepository, PlayerRepository, DraftRepository, CounterpickRepository,
    RaceResultRepository, PlayerRoundScoreRepository, ScoringRuleRepository,
    LeaderboardRepository,
    Season, Constructor, Driver, GrandPrix, League, Player, PlayerLeague,
    Draft, Counterpick, RaceResult, PlayerRoundScore, ScoringRule
)


# ============================================================
# FIXTURES
# ============================================================

@pytest_asyncio.fixture
async def mock_db():
    """Create a mock DatabaseManager"""
    db = MagicMock()
    db.fetch_one = AsyncMock()
    db.fetch_all = AsyncMock()
    db.execute_query = AsyncMock()
    return db


@pytest_asyncio.fixture
async def season_repo(mock_db):
    return SeasonRepository(mock_db)


@pytest_asyncio.fixture
async def constructor_repo(mock_db):
    return ConstructorRepository(mock_db)


@pytest_asyncio.fixture
async def driver_repo(mock_db):
    return DriverRepository(mock_db)


@pytest_asyncio.fixture
async def grand_prix_repo(mock_db):
    return GrandPrixRepository(mock_db)


@pytest_asyncio.fixture
async def league_repo(mock_db):
    return LeagueRepository(mock_db)


@pytest_asyncio.fixture
async def player_repo(mock_db):
    return PlayerRepository(mock_db)


@pytest_asyncio.fixture
async def draft_repo(mock_db):
    return DraftRepository(mock_db)


@pytest_asyncio.fixture
async def counterpick_repo(mock_db):
    return CounterpickRepository(mock_db)

@pytest_asyncio.fixture
async def counterpick_repo(mock_db):
    return CounterpickRepository(mock_db)

@pytest_asyncio.fixture
async def race_result_repo(mock_db):
    return RaceResultRepository(mock_db)


@pytest_asyncio.fixture
async def player_round_score_repo(mock_db):
    return PlayerRoundScoreRepository(mock_db)


@pytest_asyncio.fixture
async def scoring_rule_repo(mock_db):
    return ScoringRuleRepository(mock_db)


@pytest_asyncio.fixture
async def leaderboard_repo(mock_db):
    return LeaderboardRepository(mock_db)


# ============================================================
# SEASON REPOSITORY TESTS
# ============================================================

@pytest.mark.asyncio
class TestSeasonRepository:

    async def test_create_season_success(self, season_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_one.return_value = (1, 2025, False, now)

        # Act
        result = await season_repo.create_season(year=2025, is_active=False)

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.year == 2025
        assert result.is_active is False
        assert result.created_at == now
        mock_db.fetch_one.assert_called_once()

    async def test_create_season_failure(self, season_repo, mock_db):
        # Arrange
        mock_db.fetch_one.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(ValueError, match="Season creation failed"):
            await season_repo.create_season(year=2025)

    async def test_get_season_by_id_found(self, season_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_one.return_value = (1, 2025, True, now)

        # Act
        result = await season_repo.get_season_by_id(season_id=1)

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.year == 2025
        mock_db.fetch_one.assert_called_once()

    async def test_get_season_by_id_not_found(self, season_repo, mock_db):
        # Arrange
        mock_db.fetch_one.return_value = None

        # Act
        result = await season_repo.get_season_by_id(season_id=999)

        # Assert
        assert result is None

    async def test_get_active_season(self, season_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_one.return_value = (1, 2025, True, now)

        # Act
        result = await season_repo.get_active_season()

        # Assert
        assert result is not None
        assert result.is_active is True

    async def test_get_season_by_year(self, season_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_one.return_value = (1, 2025, True, now)

        # Act
        result = await season_repo.get_season_by_year(year=2025)

        # Assert
        assert result is not None
        assert result.year == 2025

    async def test_set_active_season(self, season_repo, mock_db):
        # Act
        result = await season_repo.set_active_season(season_id=1)

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()

    async def test_list_all_seasons(self, season_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_all.return_value = [
            (1, 2025, True, now),
            (2, 2024, False, now)
        ]

        # Act
        result = await season_repo.list_all_seasons()

        # Assert
        assert len(result) == 2
        assert result[0].year == 2025
        assert result[1].year == 2024


# ============================================================
# CONSTRUCTOR REPOSITORY TESTS
# ============================================================

@pytest.mark.asyncio
class TestConstructorRepository:

    async def test_create_constructor_success(self, constructor_repo, mock_db):
        # Arrange
        mock_db.fetch_one.return_value = (1, 1, "RBR", "Red Bull Racing", "#0600EF", "red_bull")

        # Act
        result = await constructor_repo.create_constructor(
            season_id=1,
            short_name="RBR",
            full_name="Red Bull Racing",
            color_hex="#0600EF",
            ergast_id="red_bull"
        )

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.short_name == "RBR"
        assert result.full_name == "Red Bull Racing"

    async def test_create_constructor_failure(self, constructor_repo, mock_db):
        # Arrange
        mock_db.fetch_one.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(ValueError, match="Constructor creation failed"):
            await constructor_repo.create_constructor(
                season_id=1,
                short_name="RBR",
                full_name="Red Bull Racing"
            )

    async def test_get_constructor_by_id(self, constructor_repo, mock_db):
        # Arrange
        mock_db.fetch_one.return_value = (1, 1, "RBR", "Red Bull Racing", "#0600EF", "red_bull")

        # Act
        result = await constructor_repo.get_constructor_by_id(constructor_id=1)

        # Assert
        assert result is not None
        assert result.id == 1

    async def test_list_constructors_by_season(self, constructor_repo, mock_db):
        # Arrange
        mock_db.fetch_all.return_value = [
            (1, 1, "RBR", "Red Bull Racing", "#0600EF", "red_bull"),
            (2, 1, "MCL", "McLaren", "#FF8700", "mclaren")
        ]

        # Act
        result = await constructor_repo.list_constructors_by_season(season_id=1)

        # Assert
        assert len(result) == 2
        assert result[0].short_name == "RBR"
        assert result[1].short_name == "MCL"

    async def test_update_constructor_all_fields(self, constructor_repo, mock_db):
        # Act
        result = await constructor_repo.update_constructor(
            constructor_id=1,
            short_name="RBR",
            full_name="Oracle Red Bull Racing",
            color_hex="#0600EF",
            ergast_id="red_bull"
        )

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()

    async def test_update_constructor_no_fields(self, constructor_repo, mock_db):
        # Act
        result = await constructor_repo.update_constructor(constructor_id=1)

        # Assert
        assert result is False
        mock_db.execute_query.assert_not_called()

    async def test_update_constructor_partial_fields(self, constructor_repo, mock_db):
        # Act
        result = await constructor_repo.update_constructor(
            constructor_id=1,
            short_name="RBR"
        )

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()

    async def test_delete_constructor(self, constructor_repo, mock_db):
        # Act
        result = await constructor_repo.delete_constructor(constructor_id=1)

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()


# ============================================================
# DRIVER REPOSITORY TESTS
# ============================================================

@pytest.mark.asyncio
class TestDriverRepository:

    async def test_create_driver_success(self, driver_repo, mock_db):
        # Arrange
        from datetime import date
        dob = datetime(1997, 9, 30)
        mock_db.fetch_one.return_value = (1, 1, "VER", 1, "Max", "Verstappen", 1, "verstappen", True, dob, "Dutch", "https://example.com/ver.jpg")

        # Act
        result = await driver_repo.create_driver(
            season_id=1,
            code="VER",
            number=1,
            first_name="Max",
            last_name="Verstappen",
            constructor_id=1,
            ergast_id="verstappen",
            is_active=True,
            date_of_birth=dob,
            nationality="Dutch",
            driver_image_url="https://example.com/ver.jpg"
        )

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.code == "VER"
        assert result.number == 1
        assert result.first_name == "Max"
        assert result.last_name == "Verstappen"
        assert result.date_of_birth == dob
        assert result.nationality == "Dutch"
        assert result.driver_image_url == "https://example.com/ver.jpg"

    async def test_create_driver_failure(self, driver_repo, mock_db):
        # Arrange
        mock_db.fetch_one.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(ValueError, match="Driver creation failed"):
            await driver_repo.create_driver(
                season_id=1,
                code="VER",
                number=1,
                first_name="Max",
                last_name="Verstappen",
                constructor_id=1
            )

    async def test_get_driver_by_id(self, driver_repo, mock_db):
        # Arrange
        dob = datetime(1997, 9, 30)
        mock_db.fetch_one.return_value = (1, 1, "VER", 1, "Max", "Verstappen", 1, "verstappen", True, dob, "Dutch", "https://example.com/ver.jpg")

        # Act
        result = await driver_repo.get_driver_by_id(driver_id=1)

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.code == "VER"
        assert result.date_of_birth == dob
        assert result.nationality == "Dutch"
        assert result.driver_image_url == "https://example.com/ver.jpg"

    async def test_list_drivers_by_season_active_only(self, driver_repo, mock_db):
        # Arrange
        dob1 = datetime(1997, 9, 30)
        dob2 = datetime(1990, 1, 26)
        mock_db.fetch_all.return_value = [
            (1, 1, "VER", 1, "Max", "Verstappen", 1, "verstappen", True, dob1, "Dutch", "https://example.com/ver.jpg"),
            (2, 1, "PER", 11, "Sergio", "Perez", 1, "perez", True, dob2, "Mexican", "https://example.com/per.jpg")
        ]

        # Act
        result = await driver_repo.list_drivers_by_season(season_id=1, active_only=True)

        # Assert
        assert len(result) == 2
        assert all(d.is_active for d in result)
        assert result[0].date_of_birth == dob1
        assert result[1].nationality == "Mexican"

    async def test_list_drivers_by_season_all(self, driver_repo, mock_db):
        # Arrange
        dob1 = datetime(1997, 9, 30)
        dob2 = datetime(1989, 7, 1)
        mock_db.fetch_all.return_value = [
            (1, 1, "VER", 1, "Max", "Verstappen", 1, "verstappen", True, dob1, "Dutch", "https://example.com/ver.jpg"),
            (2, 1, "RIC", 3, "Daniel", "Ricciardo", 1, "ricciardo", False, dob2, "Australian", None)
        ]

        # Act
        result = await driver_repo.list_drivers_by_season(season_id=1, active_only=False)

        # Assert
        assert len(result) == 2
        assert result[0].is_active is True
        assert result[1].is_active is False
        assert result[1].driver_image_url is None

    async def test_list_drivers_by_constructor(self, driver_repo, mock_db):
        # Arrange
        dob1 = datetime(1997, 9, 30)
        dob2 = datetime(1990, 1, 26)
        mock_db.fetch_all.return_value = [
            (1, 1, "VER", 1, "Max", "Verstappen", 1, "verstappen", True, dob1, "Dutch", "https://example.com/ver.jpg"),
            (2, 1, "PER", 11, "Sergio", "Perez", 1, "perez", True, dob2, "Mexican", "https://example.com/per.jpg")
        ]

        # Act
        result = await driver_repo.list_drivers_by_constructor(constructor_id=1)

        # Assert
        assert len(result) == 2
        assert all(d.constructor_id == 1 for d in result)
        assert result[0].nationality == "Dutch"
        assert result[1].nationality == "Mexican"


# ============================================================
# GRAND PRIX REPOSITORY TESTS
# ============================================================

@pytest.mark.asyncio
class TestGrandPrixRepository:

    async def test_create_grand_prix_success(self, grand_prix_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_one.return_value = (
            1, 1, 1, "Bahrain Grand Prix", "bahrain", "conventional",
            now, None, None, now, now, now, now, False
        )

        # Act
        result = await grand_prix_repo.create_grand_prix(
            season_id=1,
            round_number=1,
            event_name="Bahrain Grand Prix",
            circuit_key="bahrain",
            event_format="conventional",
            quali_date_utc=now,
            race_date_utc=now,
            draft_deadline_utc=now,
            draft_reset_utc=now,
            counterpick_deadline_utc=now
        )

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.event_name == "Bahrain Grand Prix"
        assert result.round_number == 1

    async def test_create_grand_prix_failure(self, grand_prix_repo, mock_db):
        # Arrange
        mock_db.fetch_one.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(ValueError, match="Grand Prix creation failed"):
            await grand_prix_repo.create_grand_prix(
                season_id=1,
                round_number=1,
                event_name="Bahrain Grand Prix"
            )

    async def test_get_grand_prix_by_id(self, grand_prix_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_one.return_value = (
            1, 1, 1, "Bahrain Grand Prix", "bahrain", "conventional",
            now, None, None, now, now, now, now, False
        )

        # Act
        result = await grand_prix_repo.get_grand_prix_by_id(grand_prix_id=1)

        # Assert
        assert result is not None
        assert result.id == 1

    async def test_list_grands_prix_by_season(self, grand_prix_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_all.return_value = [
            (1, 1, 1, "Bahrain Grand Prix", "bahrain", "conventional",
             now, None, None, now, now, now, now, False),
            (2, 1, 2, "Saudi Arabian Grand Prix", "jeddah", "conventional",
             now, None, None, now, now, now, now, False)
        ]

        # Act
        result = await grand_prix_repo.list_grands_prix_by_season(season_id=1)

        # Assert
        assert len(result) == 2
        assert result[0].round_number == 1
        assert result[1].round_number == 2

    async def test_get_next_grand_prix(self, grand_prix_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_one.return_value = (
            2, 1, 2, "Saudi Arabian Grand Prix", "jeddah", "conventional",
            now, None, None, now, now, now, now, False
        )

        # Act
        result = await grand_prix_repo.get_next_grand_prix(season_id=1)

        # Assert
        assert result is not None
        assert result.is_completed is False

    async def test_mark_as_completed(self, grand_prix_repo, mock_db):
        # Act
        result = await grand_prix_repo.mark_as_completed(grand_prix_id=1)

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()

    async def test_update_grand_prix_dates_all_fields(self, grand_prix_repo, mock_db):
        # Arrange
        now = datetime.now()

        # Act
        result = await grand_prix_repo.update_grand_prix_dates(
            grand_prix_id=1,
            quali_date_utc=now,
            sprint_quali_date_utc=now,
            sprint_date_utc=now,
            race_date_utc=now,
            draft_deadline_utc=now,
            draft_reset_utc=now,
            counterpick_deadline_utc=now
        )

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()

    async def test_update_grand_prix_dates_no_fields(self, grand_prix_repo, mock_db):
        # Act
        result = await grand_prix_repo.update_grand_prix_dates(grand_prix_id=1)

        # Assert
        assert result is False
        mock_db.execute_query.assert_not_called()

    async def test_delete_grand_prix(self, grand_prix_repo, mock_db):
        # Act
        result = await grand_prix_repo.delete_grand_prix(grand_prix_id=1)

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()


# ============================================================
# LEAGUE REPOSITORY TESTS
# ============================================================

@pytest.mark.asyncio
class TestLeagueRepository:

    async def test_create_league_success(self, league_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_one.return_value = (1, "Test League", 123456789, 1, 0xE8272A, now, 3)

        # Act
        result = await league_repo.create_league(
            name="Test League",
            season_id=1,
            discord_guild_id=123456789,
            embed_color=0xE8272A,
            counterpick_limit=3
        )

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.name == "Test League"
        assert result.discord_guild_id == 123456789
        assert result.counterpick_limit == 3

    async def test_create_league_failure(self, league_repo, mock_db):
        # Arrange
        mock_db.fetch_one.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(ValueError, match="League creation failed"):
            await league_repo.create_league(name="Test League", season_id=1)

    async def test_get_league_by_id(self, league_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_one.return_value = (1, "Test League", 123456789, 1, 0xE8272A, now, 3)

        # Act
        result = await league_repo.get_league_by_id(league_id=1)

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.counterpick_limit == 3

    async def test_get_league_by_discord_guild(self, league_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_one.return_value = (1, "Test League", 123456789, 1, 0xE8272A, now, 3)

        # Act
        result = await league_repo.get_league_by_discord_guild(discord_guild_id=123456789)

        # Assert
        assert result is not None
        assert result.discord_guild_id == 123456789

    async def test_get_leagues_by_discord_guild(self, league_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_all.return_value = [
            (1, "League 1", 123456789, 1, 0xE8272A, now, 3),
            (2, "League 2", 123456789, 1, 0xE8272A, now, 5)
        ]

        # Act
        result = await league_repo.get_leagues_by_discord_guild(discord_guild_id=123456789)

        # Assert
        assert len(result) == 2
        assert result[0].counterpick_limit == 3
        assert result[1].counterpick_limit == 5

    async def test_list_leagues_by_season(self, league_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_all.return_value = [
            (1, "League 1", 123456789, 1, 0xE8272A, now, 3),
            (2, "League 2", 987654321, 1, 0xE8272A, now, 3)
        ]

        # Act
        result = await league_repo.list_leagues_by_season(season_id=1)

        # Assert
        assert len(result) == 2

    async def test_get_player_count(self, league_repo, mock_db):
        # Arrange
        mock_db.fetch_one.return_value = (5,)

        # Act
        result = await league_repo.get_player_count(league_id=1)

        # Assert
        assert result == 5

    async def test_list_players_in_league(self, league_repo, mock_db):
        # Arrange
        now = datetime.now()
        # Fixed: Player table has 6 fields
        mock_db.fetch_all.return_value = [
            (1, 111, "player1", None, "UTC", now),
            (2, 222, "player2", None, "UTC", now)
        ]

        # Act
        result = await league_repo.list_players_in_league(league_id=1)

        # Assert
        assert len(result) == 2
        assert result[0].username == "player1"

    async def test_update_league_name(self, league_repo, mock_db):
        # Act
        result = await league_repo.update_league_name(league_id=1, name="New Name")

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()

    async def test_update_league_counterpick_limit(self, league_repo, mock_db):
        # Act
        result = await league_repo.update_league_counterpick_limit(league_id=1, counterpick_limit=5)

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()

    async def test_delete_league(self, league_repo, mock_db):
        # Act
        result = await league_repo.delete_league(league_id=1)

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()


# ============================================================
# PLAYER REPOSITORY TESTS
# ============================================================

@pytest.mark.asyncio
class TestPlayerRepository:

    async def test_create_player_success(self, player_repo, mock_db):
        # Arrange
        now = datetime.now()
        # Fixed: Player table has 6 fields: id, discord_user_id, username, password, timezone, created_at
        mock_db.fetch_one.return_value = (1, 123456789, "testuser", None, "UTC", now)

        # Act
        result = await player_repo.create_player(
            username="testuser",
            discord_user_id=123456789,
            timezone="UTC"
        )

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.username == "testuser"
        assert result.timezone == "UTC"

    async def test_create_player_failure(self, player_repo, mock_db):
        # Arrange
        mock_db.fetch_one.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(ValueError, match="Player creation failed"):
            await player_repo.create_player(username="testuser")

    async def test_get_player_by_id(self, player_repo, mock_db):
        # Arrange
        now = datetime.now()
        # Fixed: Player table has 6 fields
        mock_db.fetch_one.return_value = (1, 123456789, "testuser", None, "UTC", now)

        # Act
        result = await player_repo.get_player_by_id(player_id=1)

        # Assert
        assert result is not None
        assert result.id == 1

    async def test_get_player_by_discord_id(self, player_repo, mock_db):
        # Arrange
        now = datetime.now()
        # Fixed: Player table has 6 fields
        mock_db.fetch_one.return_value = (1, 123456789, "testuser", None, "UTC", now)

        # Act
        result = await player_repo.get_player_by_discord_id(discord_user_id=123456789)

        # Assert
        assert result is not None
        assert result.discord_user_id == 123456789

    async def test_get_player_by_username(self, player_repo, mock_db):
        # Arrange
        now = datetime.now()
        # Fixed: Player table has 6 fields
        mock_db.fetch_one.return_value = (1, 123456789, "testuser", None, "UTC", now)

        # Act
        result = await player_repo.get_player_by_username(username="testuser")

        # Assert
        assert result is not None
        assert result.username == "testuser"

    async def test_list_players_in_league(self, player_repo, mock_db):
        # Arrange
        now = datetime.now()
        # Fixed: Player table has 6 fields
        mock_db.fetch_all.return_value = [
            (1, 111, "player1", None, "UTC", now),
            (2, 222, "player2", None, "UTC", now)
        ]

        # Act
        result = await player_repo.list_players_in_league(league_id=1)

        # Assert
        assert len(result) == 2

    async def test_list_leagues_for_player(self, player_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_all.return_value = [
            (1, "League 1", 123456789, 1, 0xE8272A, now),
            (2, "League 2", 987654321, 1, 0xE8272A, now)
        ]

        # Act
        result = await player_repo.list_leagues_for_player(player_id=1)

        # Assert
        assert len(result) == 2

    async def test_get_leagues_for_player_by_discord_id(self, player_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_all.return_value = [
            (1, "League 1", 123456789, 1, 0xE8272A, now)
        ]

        # Act
        result = await player_repo.get_leagues_for_player_by_discord_id(discord_user_id=123456789)

        # Assert
        assert len(result) == 1

    async def test_add_player_to_league_success(self, player_repo, mock_db):
        # Arrange
        now = datetime.now()
        # Fixed: Correct order is (player_id, league_id, team_name, team_motto, joined_at)
        mock_db.fetch_one.return_value = (1, 1, "Test Team", "Test Motto", now)

        # Act
        result = await player_repo.add_player_to_league(
            player_id=1,
            league_id=1,
            team_name="Test Team",
            team_motto="Test Motto"
        )

        # Assert
        assert result is not None
        assert result.player_id == 1
        assert result.league_id == 1
        assert result.team_name == "Test Team"
        assert result.team_motto == "Test Motto"

    async def test_add_player_to_league_without_team_info(self, player_repo, mock_db):
        # Arrange
        now = datetime.now()
        # Fixed: Correct order and provide team_name and team_motto parameters
        mock_db.fetch_one.return_value = (1, 1, None, None, now)

        # Act
        result = await player_repo.add_player_to_league(
            player_id=1,
            league_id=1,
            team_name=None,
            team_motto=None
        )

        # Assert
        assert result is not None
        assert result.player_id == 1
        assert result.league_id == 1
        assert result.team_name is None
        assert result.team_motto is None

    async def test_add_player_to_league_failure(self, player_repo, mock_db):
        # Arrange
        mock_db.fetch_one.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(ValueError, match="Failed to add player to league"):
            await player_repo.add_player_to_league(
                player_id=1,
                league_id=1,
                team_name="Test Team",
                team_motto="Test Motto"
            )

    async def test_remove_player_from_league(self, player_repo, mock_db):
        # Act
        result = await player_repo.remove_player_from_league(player_id=1, league_id=1)

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()

    async def test_is_player_in_league_true(self, player_repo, mock_db):
        # Arrange
        mock_db.fetch_one.return_value = (True,)

        # Act
        result = await player_repo.is_player_in_league(player_id=1, league_id=1)

        # Assert
        assert result is True

    async def test_is_player_in_league_false(self, player_repo, mock_db):
        # Arrange
        mock_db.fetch_one.return_value = (False,)

        # Act
        result = await player_repo.is_player_in_league(player_id=1, league_id=1)

        # Assert
        assert result is False

    async def test_is_discord_user_in_league(self, player_repo, mock_db):
        # Arrange
        mock_db.fetch_one.return_value = (True,)

        # Act
        result = await player_repo.is_discord_user_in_league(discord_user_id=123456789, league_id=1)

        # Assert
        assert result is True

    async def test_get_player_count_in_league(self, player_repo, mock_db):
        # Arrange
        mock_db.fetch_one.return_value = (10,)

        # Act
        result = await player_repo.get_player_count_in_league(league_id=1)

        # Assert
        assert result == 10

    async def test_get_league_count_for_player(self, player_repo, mock_db):
        # Arrange
        mock_db.fetch_one.return_value = (3,)

        # Act
        result = await player_repo.get_league_count_for_player(player_id=1)

        # Assert
        assert result == 3

    async def test_update_team_name_success(self, player_repo, mock_db):
        # Updated: Now requires league_id parameter
        # Act
        result = await player_repo.update_team_name(player_id=1, league_id=1, team_name="New Team")

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()

    async def test_update_team_name_failure(self, player_repo, mock_db):
        # Arrange
        mock_db.execute_query.side_effect = Exception("Database error")

        # Updated: Now requires league_id parameter
        # Act
        result = await player_repo.update_team_name(player_id=1, league_id=1, team_name="New Team")

        # Assert
        assert result is False

    async def test_update_team_motto(self, player_repo, mock_db):
        # Updated: Now requires league_id parameter
        # Act
        result = await player_repo.update_team_motto(player_id=1, league_id=1, team_motto="New Motto")

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()

    async def test_get_player_league_info(self, player_repo, mock_db):
        # New test for getting league-specific player information
        # Arrange
        now = datetime.now()
        # Fixed: Correct order is (player_id, league_id, team_name, team_motto, joined_at)
        mock_db.fetch_one.return_value = (1, 1, "Team Name", "Team Motto", now)

        # Act
        result = await player_repo.get_player_league_info(player_id=1, league_id=1)

        # Assert
        assert result is not None
        assert result.player_id == 1
        assert result.league_id == 1
        assert result.team_name == "Team Name"
        assert result.team_motto == "Team Motto"

    async def test_get_player_league_info_not_found(self, player_repo, mock_db):
        # New test for when player is not in league
        # Arrange
        mock_db.fetch_one.return_value = None

        # Act
        result = await player_repo.get_player_league_info(player_id=999, league_id=1)

        # Assert
        assert result is None

    async def test_update_password(self, player_repo, mock_db):
        # Act
        result = await player_repo.update_password(player_id=1, password_hash="hashed_password")

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()

    async def test_delete_player(self, player_repo, mock_db):
        # Act
        result = await player_repo.delete_player(player_id=1)

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()


# ============================================================
# DRAFT REPOSITORY TESTS
# ============================================================

@pytest.mark.asyncio
class TestDraftRepository:

    async def test_create_draft_success(self, draft_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_one.return_value = (1, 1, 1, 1, 1, 2, 3, 4, 5, False, now, now)

        # Act
        result = await draft_repo.create_draft(
            player_id=1,
            league_id=1,
            grand_prix_id=1,
            driver1_id=1,
            driver2_id=2,
            driver3_id=3,
            wildcard_id=4,
            constructor_id=5
        )

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.driver1_id == 1
        assert result.driver2_id == 2
        assert result.driver3_id == 3

    async def test_create_draft_failure(self, draft_repo, mock_db):
        # Arrange
        mock_db.fetch_one.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(ValueError, match="Draft creation failed"):
            await draft_repo.create_draft(
                player_id=1, league_id=1, grand_prix_id=1,
                driver1_id=1, driver2_id=2, driver3_id=3,
                wildcard_id=4, constructor_id=5
            )

    async def test_get_draft(self, draft_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_one.return_value = (1, 1, 1, 1, 1, 2, 3, 4, 5, False, now, now)

        # Act
        result = await draft_repo.get_draft(player_id=1, league_id=1, grand_prix_id=1)

        # Assert
        assert result is not None
        assert result.player_id == 1
        assert result.league_id == 1

    async def test_list_drafts_for_grand_prix_in_league(self, draft_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_all.return_value = [
            (1, 1, 1, 1, 1, 2, 3, 4, 5, False, now, now),
            (2, 2, 1, 1, 6, 7, 8, 9, 10, False, now, now)
        ]

        # Act
        result = await draft_repo.list_drafts_for_grand_prix_in_league(grand_prix_id=1, league_id=1)

        # Assert
        assert len(result) == 2

    async def test_list_drafts_for_player_in_league(self, draft_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_all.return_value = [
            (1, 1, 1, 1, 1, 2, 3, 4, 5, False, now, now),
            (2, 1, 1, 2, 6, 7, 8, 9, 10, False, now, now)
        ]

        # Act
        result = await draft_repo.list_drafts_for_player_in_league(player_id=1, league_id=1)

        # Assert
        assert len(result) == 2

    async def test_get_all_drafts_for_player_for_gp(self, draft_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_all.return_value = [
            (1, 1, 1, 1, 1, 2, 3, 4, 5, False, now, now),
            (2, 1, 2, 1, 6, 7, 8, 9, 10, False, now, now)
        ]

        # Act
        result = await draft_repo.get_all_drafts_for_player_for_gp(player_id=1, grand_prix_id=1)

        # Assert
        assert len(result) == 2

    async def test_delete_draft(self, draft_repo, mock_db):
        # Act
        result = await draft_repo.delete_draft(player_id=1, league_id=1, grand_prix_id=1)

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()


# ============================================================
# COUNTERPICK REPOSITORY TESTS
# ============================================================

@pytest.mark.asyncio
class TestCounterpickRepository:

    async def test_get_remaining_counterpicks_with_usage(self, counterpick_repo, mock_db):
        # Arrange
        mock_db.fetch_one.return_value = (3, 1)  # limit=3, used=1

        # Act
        result = await counterpick_repo.get_remaining_counterpicks(
            player_id=1, league_id=1, season_id=1
        )

        # Assert
        assert result == 2

    async def test_get_remaining_counterpicks_no_usage(self, counterpick_repo, mock_db):
        # Arrange
        mock_db.fetch_one.return_value = (3, 0)  # limit=3, used=0

        # Act
        result = await counterpick_repo.get_remaining_counterpicks(
            player_id=1, league_id=1, season_id=1
        )

        # Assert
        assert result == 3

    async def test_get_remaining_counterpicks_all_used(self, counterpick_repo, mock_db):
        # Arrange
        mock_db.fetch_one.return_value = (3, 3)  # limit=3, used=3

        # Act
        result = await counterpick_repo.get_remaining_counterpicks(
            player_id=1, league_id=1, season_id=1
        )

        # Assert
        assert result == 0

    async def test_get_counterpick_usage(self, counterpick_repo, mock_db):
        # Arrange
        mock_db.fetch_one.return_value = (1, 1, 1, 2)

        # Act
        result = await counterpick_repo.get_counterpick_usage(
            player_id=1, league_id=1, season_id=1
        )

        # Assert
        assert result is not None
        assert result.player_id == 1
        assert result.used_count == 2

    async def test_get_counterpick_usage_none(self, counterpick_repo, mock_db):
        # Arrange
        mock_db.fetch_one.return_value = None

        # Act
        result = await counterpick_repo.get_counterpick_usage(
            player_id=1, league_id=1, season_id=1
        )

        # Assert
        assert result is None

    async def test_get_target_counterpick_count(self, counterpick_repo, mock_db):
        # Arrange
        mock_db.fetch_one.return_value = (2,)

        # Act
        result = await counterpick_repo.get_target_counterpick_count(
            target_player_id=2, grand_prix_id=1, league_id=1
        )

        # Assert
        assert result == 2

    async def test_can_counterpick_allowed(self, counterpick_repo, mock_db):
        # Arrange
        mock_db.fetch_one.side_effect = [
            (3, 1),  # get_remaining_counterpicks: limit=3, used=1
            None,  # get_counterpick: no existing
            (1,)  # get_target_counterpick_count: 1 existing
        ]

        # Act
        can_pick, reason = await counterpick_repo.can_counterpick(
            picking_player_id=1,
            target_player_id=2,
            grand_prix_id=1,
            league_id=1,
            season_id=1
        )

        # Assert
        assert can_pick is True
        assert reason == "Counterpick allowed"

    async def test_can_counterpick_no_remaining(self, counterpick_repo, mock_db):
        # Arrange
        mock_db.fetch_one.side_effect = [
            (3, 3),  # get_remaining_counterpicks: limit=3, used=3
            None  # get_counterpick: no existing
        ]

        # Act
        can_pick, reason = await counterpick_repo.can_counterpick(
            picking_player_id=1,
            target_player_id=2,
            grand_prix_id=1,
            league_id=1,
            season_id=1
        )

        # Assert
        assert can_pick is False
        assert "used all your counterpicks" in reason

    async def test_can_counterpick_target_at_limit(self, counterpick_repo, mock_db):
        # Arrange
        mock_db.fetch_one.side_effect = [
            (3, 1),  # get_remaining_counterpicks: limit=3, used=1
            None,  # get_counterpick: no existing
            (2,)  # get_target_counterpick_count: 2 existing (at limit)
        ]

        # Act
        can_pick, reason = await counterpick_repo.can_counterpick(
            picking_player_id=1,
            target_player_id=2,
            grand_prix_id=1,
            league_id=1,
            season_id=1
        )

        # Assert
        assert can_pick is False
        assert "maximum of 2 counterpicks" in reason

    async def test_can_counterpick_update_allowed(self, counterpick_repo, mock_db):
        # Arrange
        now = datetime.now()
        existing_counterpick = (1, 1, 1, 1, 2, 5, now)  # existing counterpick targeting player 2

        mock_db.fetch_one.side_effect = [
            (3, 2),  # get_remaining_counterpicks: limit=3, used=2
            existing_counterpick,  # get_counterpick: existing counterpick
            (1,)  # get_target_counterpick_count: 1 for new target
        ]

        # Act - changing target from player 2 to player 3
        can_pick, reason = await counterpick_repo.can_counterpick(
            picking_player_id=1,
            target_player_id=3,  # Different target
            grand_prix_id=1,
            league_id=1,
            season_id=1
        )

        # Assert
        assert can_pick is True
        assert reason == "Counterpick allowed"

    async def test_create_counterpick_success(self, counterpick_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_one.return_value = (1, 1, 1, 1, 2, 3, now)

        # Act
        result = await counterpick_repo.create_counterpick(
            grand_prix_id=1,
            league_id=1,
            picking_player_id=1,
            target_player_id=2,
            target_driver_id=3
        )

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.picking_player_id == 1
        assert result.target_player_id == 2

    async def test_create_counterpick_failure(self, counterpick_repo, mock_db):
        # Arrange
        mock_db.fetch_one.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(ValueError, match="Counterpick creation failed"):
            await counterpick_repo.create_counterpick(
                grand_prix_id=1, league_id=1,
                picking_player_id=1, target_player_id=2, target_driver_id=3
            )

    async def test_get_counterpick(self, counterpick_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_one.return_value = (1, 1, 1, 1, 2, 3, now)

        # Act
        result = await counterpick_repo.get_counterpick(
            grand_prix_id=1, league_id=1, picking_player_id=1
        )

        # Assert
        assert result is not None
        assert result.picking_player_id == 1

    async def test_list_counterpicks_for_grand_prix(self, counterpick_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_all.return_value = [
            (1, 1, 1, 1, 2, 3, now),
            (2, 1, 1, 2, 3, 4, now)
        ]

        # Act
        result = await counterpick_repo.list_counterpicks_for_grand_prix(grand_prix_id=1, league_id=1)

        # Assert
        assert len(result) == 2

    async def test_list_counterpicks_targeting_player(self, counterpick_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_all.return_value = [
            (1, 1, 1, 1, 2, 3, now),
            (2, 1, 1, 3, 2, 4, now)
        ]

        # Act
        result = await counterpick_repo.list_counterpicks_targeting_player(
            grand_prix_id=1, league_id=1, target_player_id=2
        )

        # Assert
        assert len(result) == 2

    async def test_get_counterpicks_by_player_across_leagues(self, counterpick_repo, mock_db):
        # Arrange
        now = datetime.now()
        mock_db.fetch_all.return_value = [
            (1, 1, 1, 1, 2, 3, now),
            (2, 1, 2, 1, 3, 4, now)
        ]

        # Act
        result = await counterpick_repo.get_counterpicks_by_player_across_leagues(
            player_id=1, grand_prix_id=1
        )

        # Assert
        assert len(result) == 2

    async def test_delete_counterpick(self, counterpick_repo, mock_db):
        # Act
        result = await counterpick_repo.delete_counterpick(
            grand_prix_id=1, league_id=1, picking_player_id=1
        )

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()


# ============================================================
# RACE RESULT REPOSITORY TESTS
# ============================================================

@pytest.mark.asyncio
class TestRaceResultRepository:

    async def test_create_race_result_success(self, race_result_repo, mock_db):
        # Arrange
        mock_db.fetch_one.return_value = (1, 1, "race", 1, 1)

        # Act
        result = await race_result_repo.create_race_result(
            grand_prix_id=1,
            session_type="race",
            driver_id=1,
            position=1
        )

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.position == 1
        assert result.session_type == "race"

    async def test_create_race_result_failure(self, race_result_repo, mock_db):
        # Arrange
        mock_db.fetch_one.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(ValueError, match="Race result creation failed"):
            await race_result_repo.create_race_result(
                grand_prix_id=1, session_type="race",
                driver_id=1, position=1
            )

    async def test_get_race_results_by_session(self, race_result_repo, mock_db):
        # Arrange
        mock_db.fetch_all.return_value = [
            (1, 1, "race", 1, 1),
            (2, 1, "race", 2, 2)
        ]

        # Act
        result = await race_result_repo.get_race_results_by_session(
            grand_prix_id=1, session_type="race"
        )

        # Assert
        assert len(result) == 2
        assert result[0].position == 1
        assert result[1].position == 2

    async def test_get_all_race_results_for_gp(self, race_result_repo, mock_db):
        # Arrange
        mock_db.fetch_all.return_value = [
            (1, 1, "quali", 1, 1),
            (2, 1, "race", 1, 1)
        ]

        # Act
        result = await race_result_repo.get_all_race_results_for_gp(grand_prix_id=1)

        # Assert
        assert len(result) == 2

    async def test_delete_race_results_for_session(self, race_result_repo, mock_db):
        # Act
        result = await race_result_repo.delete_race_results_for_session(
            grand_prix_id=1, session_type="race"
        )

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()


# ============================================================
# PLAYER ROUND SCORE REPOSITORY TESTS
# ============================================================

@pytest.mark.asyncio
class TestPlayerRoundScoreRepository:

    async def test_create_or_update_score_success(self, player_round_score_repo, mock_db):
        # Arrange
        now = datetime.now()
        breakdown = {"quali": 10, "race": 15}
        mock_db.fetch_one.return_value = (1, 1, 1, 1, 25, breakdown, now)

        # Act
        result = await player_round_score_repo.create_or_update_score(
            player_id=1,
            league_id=1,
            grand_prix_id=1,
            total_points=25,
            breakdown_json=breakdown
        )

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.total_points == 25
        assert result.breakdown_json == breakdown

    async def test_create_or_update_score_failure(self, player_round_score_repo, mock_db):
        # Arrange
        mock_db.fetch_one.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(ValueError, match="Score creation failed"):
            await player_round_score_repo.create_or_update_score(
                player_id=1, league_id=1, grand_prix_id=1,
                total_points=25, breakdown_json={}
            )

    async def test_get_score(self, player_round_score_repo, mock_db):
        # Arrange
        now = datetime.now()
        breakdown = {"quali": 10, "race": 15}
        mock_db.fetch_one.return_value = (1, 1, 1, 1, 25, breakdown, now)

        # Act
        result = await player_round_score_repo.get_score(
            player_id=1, league_id=1, grand_prix_id=1
        )

        # Assert
        assert result is not None
        assert result.total_points == 25

    async def test_list_scores_for_player_in_league(self, player_round_score_repo, mock_db):
        # Arrange
        now = datetime.now()
        breakdown = {"quali": 10}
        mock_db.fetch_all.return_value = [
            (1, 1, 1, 1, 25, breakdown, now),
            (2, 1, 1, 2, 30, breakdown, now)
        ]

        # Act
        result = await player_round_score_repo.list_scores_for_player_in_league(
            player_id=1, league_id=1
        )

        # Assert
        assert len(result) == 2

    async def test_list_scores_for_grand_prix_in_league(self, player_round_score_repo, mock_db):
        # Arrange
        now = datetime.now()
        breakdown = {"quali": 10}
        mock_db.fetch_all.return_value = [
            (1, 1, 1, 1, 25, breakdown, now),
            (2, 2, 1, 1, 30, breakdown, now)
        ]

        # Act
        result = await player_round_score_repo.list_scores_for_grand_prix_in_league(
            grand_prix_id=1, league_id=1
        )

        # Assert
        assert len(result) == 2

    async def test_get_all_scores_for_player_for_gp(self, player_round_score_repo, mock_db):
        # Arrange
        now = datetime.now()
        breakdown = {"quali": 10}
        mock_db.fetch_all.return_value = [
            (1, 1, 1, 1, 25, breakdown, now),
            (2, 1, 2, 1, 30, breakdown, now)
        ]

        # Act
        result = await player_round_score_repo.get_all_scores_for_player_for_gp(
            player_id=1, grand_prix_id=1
        )

        # Assert
        assert len(result) == 2

    async def test_delete_score(self, player_round_score_repo, mock_db):
        # Act
        result = await player_round_score_repo.delete_score(
            player_id=1, league_id=1, grand_prix_id=1
        )

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()


# ============================================================
# SCORING RULE REPOSITORY TESTS
# ============================================================

@pytest.mark.asyncio
class TestScoringRuleRepository:

    async def test_create_or_update_rule_success(self, scoring_rule_repo, mock_db):
        # Arrange
        rule_value = [25, 18, 15, 12, 10]
        mock_db.fetch_one.return_value = (1, 1, "race_points", rule_value)

        # Act
        result = await scoring_rule_repo.create_or_update_rule(
            season_id=1,
            rule_key="race_points",
            rule_value=rule_value
        )

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.rule_key == "race_points"
        assert result.rule_value == rule_value

    async def test_create_or_update_rule_failure(self, scoring_rule_repo, mock_db):
        # Arrange
        mock_db.fetch_one.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(ValueError, match="Scoring rule creation failed"):
            await scoring_rule_repo.create_or_update_rule(
                season_id=1, rule_key="race_points", rule_value=[25, 18]
            )

    async def test_get_rule(self, scoring_rule_repo, mock_db):
        # Arrange
        rule_value = [25, 18, 15]
        mock_db.fetch_one.return_value = (1, 1, "race_points", rule_value)

        # Act
        result = await scoring_rule_repo.get_rule(season_id=1, rule_key="race_points")

        # Assert
        assert result is not None
        assert result.rule_key == "race_points"

    async def test_list_rules_for_season(self, scoring_rule_repo, mock_db):
        # Arrange
        mock_db.fetch_all.return_value = [
            (1, 1, "race_points", [25, 18, 15]),
            (2, 1, "quali_points", [10, 8, 6])
        ]

        # Act
        result = await scoring_rule_repo.list_rules_for_season(season_id=1)

        # Assert
        assert len(result) == 2

    async def test_delete_rule(self, scoring_rule_repo, mock_db):
        # Act
        result = await scoring_rule_repo.delete_rule(season_id=1, rule_key="race_points")

        # Assert
        assert result is True
        mock_db.execute_query.assert_called_once()


# ============================================================
# LEADERBOARD REPOSITORY TESTS
# ============================================================

@pytest.mark.asyncio
class TestLeaderboardRepository:

    async def test_get_league_leaderboard(self, leaderboard_repo, mock_db):
        # Arrange
        mock_db.fetch_all.return_value = [
            (1, "player1", "Team 1", 100, 5),
            (2, "player2", "Team 2", 95, 5)
        ]

        # Act
        result = await leaderboard_repo.get_league_leaderboard(league_id=1)

        # Assert
        assert len(result) == 2
        assert result[0]["player_id"] == 1
        assert result[0]["total_points"] == 100
        assert result[1]["total_points"] == 95

    async def test_get_grand_prix_leaderboard_with_league(self, leaderboard_repo, mock_db):
        # Arrange
        breakdown = {"quali": 10, "race": 15}
        mock_db.fetch_all.return_value = [
            (1, "player1", "Team 1", 25, breakdown),
            (2, "player2", "Team 2", 20, breakdown)
        ]

        # Act
        result = await leaderboard_repo.get_grand_prix_leaderboard(
            grand_prix_id=1, league_id=1
        )

        # Assert
        assert len(result) == 2
        assert result[0]["total_points"] == 25

    async def test_get_grand_prix_leaderboard_without_league(self, leaderboard_repo, mock_db):
        # Arrange
        breakdown = {"quali": 10}
        mock_db.fetch_all.return_value = [
            (1, "player1", "Team 1", 25, breakdown)
        ]

        # Act
        result = await leaderboard_repo.get_grand_prix_leaderboard(grand_prix_id=1)

        # Assert
        assert len(result) == 1

    async def test_get_player_league_stats(self, leaderboard_repo, mock_db):
        # Arrange
        mock_db.fetch_one.return_value = (5, 125, 25.0, 30, 20, 10)

        # Act
        result = await leaderboard_repo.get_player_league_stats(player_id=1, league_id=1)

        # Assert
        assert result is not None
        assert result["rounds_participated"] == 5
        assert result["total_points"] == 125
        assert result["avg_points_per_round"] == 25.0
        assert result["best_round_score"] == 30
        assert result["worst_round_score"] == 20

    async def test_get_player_league_stats_not_found(self, leaderboard_repo, mock_db):
        # Arrange
        mock_db.fetch_one.return_value = None

        # Act
        result = await leaderboard_repo.get_player_league_stats(player_id=999, league_id=1)

        # Assert
        assert result is None

    async def test_get_league_standings_with_rankings(self, leaderboard_repo, mock_db):
        # Arrange
        mock_db.fetch_all.return_value = [
            (1, "player1", "Team 1", 100, 5, 1, 5),
            (2, "player2", "Team 2", 95, 5, 2, 10),
            (3, "player3", "Team 3", 85, 5, 3, 0)
        ]

        # Act
        result = await leaderboard_repo.get_league_standings_with_rankings(league_id=1)

        # Assert
        assert len(result) == 3
        assert result[0]["rank"] == 1
        assert result[0]["total_points"] == 100
        assert result[0]["gap_to_next"] == 5
        assert result[1]["rank"] == 2
        assert result[1]["gap_to_next"] == 10