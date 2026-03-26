import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import json

from f1bot.services.f1service import JolpicaF1Service
from f1bot.services.models import (
    Driver,
    Constructor,
    GrandPrix,
    DriverRepository,
    ConstructorRepository,
    GrandPrixRepository,
)


@pytest.fixture
def mock_db():
    """Mock DatabaseManager for testing"""
    db = AsyncMock()
    return db


@pytest.fixture
def mock_session():
    """Mock aiohttp ClientSession"""
    session = AsyncMock()
    return session


@pytest.fixture
def f1_service(mock_db):
    """Create JolpicaF1Service instance with mocked database"""
    return JolpicaF1Service(mock_db)


@pytest.mark.asyncio
class TestJolpicaF1ServiceSetup:
    """Test async context manager and session management"""

    async def test_context_manager_enter(self, f1_service):
        """Test that __aenter__ creates a session"""
        async with f1_service as service:
            assert service.session is not None

    async def test_context_manager_exit(self, f1_service):
        """Test that __aexit__ closes the session"""
        async with f1_service as service:
            session = service.session
            session.close = AsyncMock()

        # Session should be closed after exiting context
        session.close.assert_called_once()

    async def test_get_without_session_raises_error(self, f1_service):
        """Test that calling _get without session raises RuntimeError"""
        with pytest.raises(RuntimeError, match="HTTP session not initialized"):
            await f1_service._get("test/endpoint")


@pytest.mark.asyncio
class TestJolpicaF1ServiceDrivers:
    """Test driver-related methods"""

    async def test_fetch_drivers_for_season_success(self, f1_service):
        """Test successful driver fetch from API"""
        mock_response = {
            "MRData": {
                "DriverTable": {
                    "Drivers": [
                        {
                            "driverId": "verstappen",
                            "code": "VER",
                            "permanentNumber": "1",
                            "givenName": "Max",
                            "familyName": "Verstappen"
                        },
                        {
                            "driverId": "perez",
                            "code": "PER",
                            "permanentNumber": "11",
                            "givenName": "Sergio",
                            "familyName": "Perez"
                        }
                    ]
                }
            }
        }

        with patch.object(f1_service, '_get', return_value=mock_response):
            result = await f1_service.fetch_drivers_for_season(2024)

        assert len(result) == 2
        assert result[0]["driverId"] == "verstappen"
        assert result[1]["code"] == "PER"

    async def test_fetch_drivers_for_season_failure(self, f1_service):
        """Test driver fetch handling API errors"""
        with patch.object(f1_service, '_get', side_effect=Exception("API Error")):
            result = await f1_service.fetch_drivers_for_season(2024)

        assert result == []

    async def test_sync_drivers_for_season_new_driver(self, f1_service, mock_db):
        """Test syncing drivers creates new drivers in database"""
        # Mock API response
        api_drivers = [
            {
                "driverId": "verstappen",
                "code": "VER",
                "permanentNumber": "1",
                "givenName": "Max",
                "familyName": "Verstappen"
            }
        ]

        # Mock driver repository methods
        mock_driver = Driver(
            id=1,
            season_id=1,
            code="VER",
            number=1,
            first_name="Max",
            last_name="Verstappen",
            constructor_id=1,
            ergast_id="verstappen",
            is_active=True
        )

        with patch.object(f1_service, 'fetch_drivers_for_season', return_value=api_drivers), \
                patch.object(f1_service, '_get_driver_constructor_id', return_value=1), \
                patch.object(f1_service.driver_repo, 'list_drivers_by_season', return_value=[]), \
                patch.object(f1_service.driver_repo, 'create_driver', return_value=mock_driver):
            result = await f1_service.sync_drivers_for_season(season_id=1, year=2024)

        assert len(result) == 1
        assert result[0].ergast_id == "verstappen"

    async def test_sync_drivers_for_season_existing_driver(self, f1_service, mock_db):
        """Test syncing drivers updates existing drivers"""
        api_drivers = [
            {
                "driverId": "verstappen",
                "code": "VER",
                "permanentNumber": "1",
                "givenName": "Max",
                "familyName": "Verstappen"
            }
        ]

        existing_driver = Driver(
            id=1,
            season_id=1,
            code="VER",
            number=1,
            first_name="Max",
            last_name="Verstappen",
            constructor_id=2,  # Different constructor
            ergast_id="verstappen",
            is_active=True
        )

        with patch.object(f1_service, 'fetch_drivers_for_season', return_value=api_drivers), \
                patch.object(f1_service, '_get_driver_constructor_id', return_value=1), \
                patch.object(f1_service.driver_repo, 'list_drivers_by_season', return_value=[existing_driver]), \
                patch.object(f1_service.driver_repo, 'update_driver_constructor', return_value=True) as mock_update:
            result = await f1_service.sync_drivers_for_season(season_id=1, year=2024)

        mock_update.assert_called_once_with(1, 1)
        assert len(result) == 1

    async def test_sync_drivers_no_constructor_found(self, f1_service, mock_db):
        """Test syncing drivers skips drivers without constructors"""
        api_drivers = [
            {
                "driverId": "verstappen",
                "code": "VER",
                "permanentNumber": "1",
                "givenName": "Max",
                "familyName": "Verstappen"
            }
        ]

        with patch.object(f1_service, 'fetch_drivers_for_season', return_value=api_drivers), \
                patch.object(f1_service, '_get_driver_constructor_id', return_value=None), \
                patch.object(f1_service.driver_repo, 'list_drivers_by_season', return_value=[]):
            result = await f1_service.sync_drivers_for_season(season_id=1, year=2024)

        assert len(result) == 0

    async def test_get_driver_constructor_id_success(self, f1_service, mock_db):
        """Test getting constructor ID from standings"""
        mock_response = {
            "MRData": {
                "StandingsTable": {
                    "StandingsLists": [
                        {
                            "DriverStandings": [
                                {
                                    "Constructors": [
                                        {"constructorId": "red_bull"}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }
        }

        mock_constructor = Constructor(
            id=1,
            season_id=1,
            short_name="RBR",
            full_name="Red Bull Racing",
            color_hex="#0600EF",
            ergast_id="red_bull"
        )

        with patch.object(f1_service, '_get', return_value=mock_response), \
                patch.object(f1_service.constructor_repo, 'list_constructors_by_season',
                             return_value=[mock_constructor]):
            result = await f1_service._get_driver_constructor_id(
                season_id=1,
                driver_ergast_id="verstappen",
                year=2024
            )

        assert result == 1

    async def test_get_driver_constructor_id_not_found(self, f1_service, mock_db):
        """Test getting constructor ID returns None when not found"""
        mock_response = {
            "MRData": {
                "StandingsTable": {
                    "StandingsLists": []
                }
            }
        }

        with patch.object(f1_service, '_get', return_value=mock_response):
            result = await f1_service._get_driver_constructor_id(
                season_id=1,
                driver_ergast_id="verstappen",
                year=2024
            )

        assert result is None


@pytest.mark.asyncio
class TestJolpicaF1ServiceConstructors:
    """Test constructor-related methods"""

    async def test_fetch_constructors_for_season_success(self, f1_service):
        """Test successful constructor fetch from API"""
        mock_response = {
            "MRData": {
                "ConstructorTable": {
                    "Constructors": [
                        {
                            "constructorId": "red_bull",
                            "name": "Red Bull"
                        },
                        {
                            "constructorId": "ferrari",
                            "name": "Ferrari"
                        }
                    ]
                }
            }
        }

        with patch.object(f1_service, '_get', return_value=mock_response):
            result = await f1_service.fetch_constructors_for_season(2024)

        assert len(result) == 2
        assert result[0]["constructorId"] == "red_bull"
        assert result[1]["name"] == "Ferrari"

    async def test_fetch_constructors_for_season_failure(self, f1_service):
        """Test constructor fetch handling API errors"""
        with patch.object(f1_service, '_get', side_effect=Exception("API Error")):
            result = await f1_service.fetch_constructors_for_season(2024)

        assert result == []

    async def test_sync_constructors_for_season_new(self, f1_service, mock_db):
        """Test syncing creates new constructors"""
        api_constructors = [
            {
                "constructorId": "red_bull",
                "name": "Red Bull Racing"
            }
        ]

        mock_constructor = Constructor(
            id=1,
            season_id=1,
            short_name="RBR",
            full_name="Red Bull Racing",
            color_hex="#0600EF",
            ergast_id="red_bull"
        )

        with patch.object(f1_service, 'fetch_constructors_for_season', return_value=api_constructors), \
                patch.object(f1_service.constructor_repo, 'list_constructors_by_season', return_value=[]), \
                patch.object(f1_service.constructor_repo, 'create_constructor', return_value=mock_constructor):
            result = await f1_service.sync_constructors_for_season(season_id=1, year=2024)

        assert len(result) == 1
        assert result[0].ergast_id == "red_bull"

    async def test_sync_constructors_for_season_existing(self, f1_service, mock_db):
        """Test syncing updates existing constructors"""
        api_constructors = [
            {
                "constructorId": "red_bull",
                "name": "Red Bull Racing"
            }
        ]

        existing_constructor = Constructor(
            id=1,
            season_id=1,
            short_name="RBR",
            full_name="Red Bull",
            color_hex="#0600EF",
            ergast_id="red_bull"
        )

        with patch.object(f1_service, 'fetch_constructors_for_season', return_value=api_constructors), \
                patch.object(f1_service.constructor_repo, 'list_constructors_by_season',
                             return_value=[existing_constructor]), \
                patch.object(f1_service.constructor_repo, 'update_constructor', return_value=True) as mock_update:
            result = await f1_service.sync_constructors_for_season(season_id=1, year=2024)

        mock_update.assert_called_once()
        assert len(result) == 1

    async def test_sync_constructors_with_custom_colors(self, f1_service, mock_db):
        """Test syncing constructors with custom color mapping"""
        api_constructors = [
            {
                "constructorId": "red_bull",
                "name": "Red Bull Racing"
            }
        ]

        custom_colors = {"red_bull": "#FF0000"}

        mock_constructor = Constructor(
            id=1,
            season_id=1,
            short_name="RBR",
            full_name="Red Bull Racing",
            color_hex="#FF0000",
            ergast_id="red_bull"
        )

        with patch.object(f1_service, 'fetch_constructors_for_season', return_value=api_constructors), \
                patch.object(f1_service.constructor_repo, 'list_constructors_by_season', return_value=[]), \
                patch.object(f1_service.constructor_repo, 'create_constructor',
                             return_value=mock_constructor) as mock_create:
            result = await f1_service.sync_constructors_for_season(
                season_id=1,
                year=2024,
                color_mapping=custom_colors
            )

        # Verify custom color was used
        call_args = mock_create.call_args
        assert call_args[1]['color_hex'] == "#FF0000"


@pytest.mark.asyncio
class TestJolpicaF1ServiceGrandsPrix:
    """Test Grand Prix-related methods"""

    async def test_fetch_race_schedule_for_season_success(self, f1_service):
        """Test successful race schedule fetch from API"""
        mock_response = {
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "round": "1",
                            "raceName": "Bahrain Grand Prix",
                            "Circuit": {"circuitId": "bahrain"},
                            "date": "2024-03-02",
                            "time": "15:00:00Z"
                        }
                    ]
                }
            }
        }

        with patch.object(f1_service, '_get', return_value=mock_response):
            result = await f1_service.fetch_race_schedule_for_season(2024)

        assert len(result) == 1
        assert result[0]["raceName"] == "Bahrain Grand Prix"
        assert result[0]["round"] == "1"

    async def test_fetch_race_schedule_for_season_failure(self, f1_service):
        """Test race schedule fetch handling API errors"""
        with patch.object(f1_service, '_get', side_effect=Exception("API Error")):
            result = await f1_service.fetch_race_schedule_for_season(2024)

        assert result == []

    async def test_sync_grands_prix_conventional_format(self, f1_service, mock_db):
        """Test syncing Grand Prix with conventional format"""
        api_races = [
            {
                "round": "1",
                "raceName": "Bahrain Grand Prix",
                "Circuit": {"circuitId": "bahrain"},
                "date": "2024-03-02",
                "time": "15:00:00Z",
                "Qualifying": {
                    "date": "2024-03-01",
                    "time": "15:00:00Z"
                }
            }
        ]

        mock_gp = GrandPrix(
            id=1,
            season_id=1,
            round_number=1,
            event_name="Bahrain Grand Prix",
            circuit_key="bahrain",
            event_format="conventional",
            quali_date_utc=datetime.fromisoformat("2024-03-01T15:00:00+00:00"),
            sprint_quali_date_utc=None,
            sprint_date_utc=None,
            race_date_utc=datetime.fromisoformat("2024-03-02T15:00:00+00:00"),
            draft_deadline_utc=None,
            draft_reset_utc=None,
            counterpick_deadline_utc=None,
            is_completed=False
        )

        with patch.object(f1_service, 'fetch_race_schedule_for_season', return_value=api_races), \
                patch.object(f1_service.grand_prix_repo, 'list_grands_prix_by_season', return_value=[]), \
                patch.object(f1_service.grand_prix_repo, 'create_grand_prix', return_value=mock_gp) as mock_create:
            result = await f1_service.sync_grands_prix_for_season(season_id=1, year=2024)

        assert len(result) == 1
        assert result[0].event_format == "conventional"
        mock_create.assert_called_once()

    async def test_sync_grands_prix_sprint_format(self, f1_service, mock_db):
        """Test syncing Grand Prix with sprint format"""
        api_races = [
            {
                "round": "1",
                "raceName": "Miami Grand Prix",
                "Circuit": {"circuitId": "miami"},
                "date": "2024-05-05",
                "time": "15:00:00Z",
                "Sprint": {
                    "date": "2024-05-04",
                    "time": "15:00:00Z"
                },
                "Qualifying": {
                    "date": "2024-05-03",
                    "time": "15:00:00Z"
                }
            }
        ]

        mock_gp = GrandPrix(
            id=1,
            season_id=1,
            round_number=1,
            event_name="Miami Grand Prix",
            circuit_key="miami",
            event_format="sprint_qualifying",
            quali_date_utc=datetime.fromisoformat("2024-05-03T15:00:00+00:00"),
            sprint_quali_date_utc=None,
            sprint_date_utc=datetime.fromisoformat("2024-05-04T15:00:00+00:00"),
            race_date_utc=datetime.fromisoformat("2024-05-05T15:00:00+00:00"),
            draft_deadline_utc=None,
            draft_reset_utc=None,
            counterpick_deadline_utc=None,
            is_completed=False
        )

        with patch.object(f1_service, 'fetch_race_schedule_for_season', return_value=api_races), \
                patch.object(f1_service.grand_prix_repo, 'list_grands_prix_by_season', return_value=[]), \
                patch.object(f1_service.grand_prix_repo, 'create_grand_prix', return_value=mock_gp) as mock_create:
            result = await f1_service.sync_grands_prix_for_season(season_id=1, year=2024)

        assert len(result) == 1
        assert result[0].event_format == "sprint_qualifying"

    async def test_sync_grands_prix_updates_existing(self, f1_service, mock_db):
        """Test syncing updates existing Grand Prix dates"""
        api_races = [
            {
                "round": "1",
                "raceName": "Bahrain Grand Prix",
                "Circuit": {"circuitId": "bahrain"},
                "date": "2024-03-02",
                "time": "15:00:00Z"
            }
        ]

        existing_gp = GrandPrix(
            id=1,
            season_id=1,
            round_number=1,
            event_name="Bahrain Grand Prix",
            circuit_key="bahrain",
            event_format="conventional",
            quali_date_utc=None,
            sprint_quali_date_utc=None,
            sprint_date_utc=None,
            race_date_utc=None,
            draft_deadline_utc=None,
            draft_reset_utc=None,
            counterpick_deadline_utc=None,
            is_completed=False
        )

        with patch.object(f1_service, 'fetch_race_schedule_for_season', return_value=api_races), \
                patch.object(f1_service.grand_prix_repo, 'list_grands_prix_by_season', return_value=[existing_gp]), \
                patch.object(f1_service.grand_prix_repo, 'update_grand_prix_dates', return_value=True) as mock_update:
            result = await f1_service.sync_grands_prix_for_season(season_id=1, year=2024)

        mock_update.assert_called_once()
        assert len(result) == 1


@pytest.mark.asyncio
class TestJolpicaF1ServiceBatchSync:
    """Test batch synchronization operations"""

    async def test_sync_season_data_success(self, f1_service, mock_db):
        """Test syncing all season data"""
        mock_constructors = [
            Constructor(
                id=1,
                season_id=1,
                short_name="RBR",
                full_name="Red Bull Racing",
                color_hex="#0600EF",
                ergast_id="red_bull"
            )
        ]

        mock_drivers = [
            Driver(
                id=1,
                season_id=1,
                code="VER",
                number=1,
                first_name="Max",
                last_name="Verstappen",
                constructor_id=1,
                ergast_id="verstappen",
                is_active=True
            )
        ]

        mock_races = [
            GrandPrix(
                id=1,
                season_id=1,
                round_number=1,
                event_name="Bahrain Grand Prix",
                circuit_key="bahrain",
                event_format="conventional",
                quali_date_utc=None,
                sprint_quali_date_utc=None,
                sprint_date_utc=None,
                race_date_utc=None,
                draft_deadline_utc=None,
                draft_reset_utc=None,
                counterpick_deadline_utc=None,
                is_completed=False
            )
        ]

        with patch.object(f1_service, 'sync_constructors_for_season', return_value=mock_constructors), \
                patch.object(f1_service, 'sync_drivers_for_season', return_value=mock_drivers), \
                patch.object(f1_service, 'sync_grands_prix_for_season', return_value=mock_races):
            result = await f1_service.sync_season_data(
                season_id=1,
                year=2024
            )

        assert len(result["constructors"]) == 1
        assert len(result["drivers"]) == 1
        assert len(result["races"]) == 1

    async def test_sync_season_data_with_custom_colors(self, f1_service, mock_db):
        """Test syncing season data with custom constructor colors"""
        custom_colors = {"red_bull": "#FF0000"}

        with patch.object(f1_service, 'sync_constructors_for_season', return_value=[]) as mock_sync_constructors, \
                patch.object(f1_service, 'sync_drivers_for_season', return_value=[]), \
                patch.object(f1_service, 'sync_grands_prix_for_season', return_value=[]):
            await f1_service.sync_season_data(
                season_id=1,
                year=2024,
                constructor_colors=custom_colors
            )

        # Verify custom colors were passed to constructor sync
        mock_sync_constructors.assert_called_once_with(1, 2024, custom_colors)


@pytest.mark.asyncio
class TestJolpicaF1ServiceIntegration:
    """Integration tests for the service"""

    async def test_api_get_request(self, f1_service):
        """Test making an actual GET request (mocked response)"""
        mock_json = {"test": "data"}

        async with f1_service as service:
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value=mock_json)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            service.session.get = MagicMock(return_value=mock_response)

            result = await service._get("test/endpoint")

        assert result == mock_json
        service.session.get.assert_called_once_with(
            f"{JolpicaF1Service.BASE_URL}/test/endpoint",
            params=None
        )

    async def test_api_get_with_params(self, f1_service):
        """Test making GET request with query parameters"""
        mock_json = {"test": "data"}
        params = {"limit": "10"}

        async with f1_service as service:
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = AsyncMock(return_value=mock_json)
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            service.session.get = MagicMock(return_value=mock_response)

            result = await service._get("test/endpoint", params=params)

        service.session.get.assert_called_once_with(
            f"{JolpicaF1Service.BASE_URL}/test/endpoint",
            params=params
        )