from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict
from f1bot.services.models import (
    GrandPrix, Draft, Driver, Constructor, Counterpick, DriverExhaustion,
    DraftRepository, DriverRepository, ConstructorRepository,
    GrandPrixRepository, CounterpickRepository, DriverExhaustionRepository,
    DatabaseManager, ConstructorExhaustionRepository
)


class DraftValidationError(Exception):
    """Custom exception for draft validation errors"""
    pass


class DraftService:
    """
    Service for handling draft operations with comprehensive validation.
    Enforces all draft rules at the application level.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.draft_repo = DraftRepository(db_manager)
        self.driver_repo = DriverRepository(db_manager)
        self.constructor_repo = ConstructorRepository(db_manager)
        self.grand_prix_repo = GrandPrixRepository(db_manager)
        self.counterpick_repo = CounterpickRepository(db_manager)
        self.exhaustion_repo = DriverExhaustionRepository(db_manager)
        self.constructor_exhaustion_repo = ConstructorExhaustionRepository(db_manager)

    async def validate_draft_deadline(self, grand_prix_id: int) -> Tuple[bool, Optional[str]]:
        """
        Check if the draft deadline for a grand prix has passed

        Returns:
            Tuple of (is_valid, error_message)
        """
        grand_prix = await self.grand_prix_repo.get_grand_prix_by_id(grand_prix_id)

        if not grand_prix:
            return False, "Grand Prix not found"

        if grand_prix.is_completed:
            return False, "This Grand Prix has already been completed"

        if grand_prix.draft_deadline_utc:
            now = datetime.now(timezone.utc)
            if now > grand_prix.draft_deadline_utc:
                return False, f"Draft deadline has passed (was {grand_prix.draft_deadline_utc.strftime('%Y-%m-%d %H:%M UTC')})"

        return True, None

    async def validate_unique_drivers(
            self,
            driver1_id: int,
            driver2_id: int,
            driver3_id: int,
            wildcard_id: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that all 4 drafted drivers are unique

        Returns:
            Tuple of (is_valid, error_message)
        """
        driver_ids = [driver1_id, driver2_id, driver3_id, wildcard_id]

        if len(driver_ids) != len(set(driver_ids)):
            return False, "All 4 drivers must be unique. You cannot draft the same driver twice."

        return True, None

    async def validate_constructor_representation(
            self,
            driver1_id: int,
            driver2_id: int,
            driver3_id: int,
            wildcard_id: int,
            constructor_id: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that the drafted constructor is represented by at least one driver

        Returns:
            Tuple of (is_valid, error_message)
        """
        driver_ids = [driver1_id, driver2_id, driver3_id, wildcard_id]

        # Get all drivers
        drivers = await self.driver_repo.list_drivers_by_constructor(constructor_id)
        constructor_driver_ids = {d.id for d in drivers}

        # Check if at least one drafted driver belongs to the constructor
        if not any(driver_id in constructor_driver_ids for driver_id in driver_ids):
            constructor = await self.constructor_repo.get_constructor_by_id(constructor_id)
            constructor_name = constructor.full_name if constructor else f"Constructor ID {constructor_id}"
            return False, f"At least one of your drafted drivers must belong to {constructor_name}"

        return True, None

    async def validate_minimum_constructors(
            self,
            driver1_id: int,
            driver2_id: int,
            driver3_id: int,
            wildcard_id: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that at least 3 different constructors are represented among the 4 drivers

        Returns:
            Tuple of (is_valid, error_message)
        """
        driver_ids = [driver1_id, driver2_id, driver3_id, wildcard_id]

        # Get constructor IDs for all drivers
        constructor_ids = set()
        for driver_id in driver_ids:
            driver = await self.driver_repo.get_driver_by_id(driver_id)
            if driver:
                constructor_ids.add(driver.constructor_id)

        if len(constructor_ids) < 3:
            return False, f"Your 4 drivers must represent at least 3 different constructors. Currently representing only {len(constructor_ids)} constructor(s)."

        return True, None

    async def validate_driver_exhaustion(
            self,
            player_id: int,
            league_id: int,
            driver1_id: int,
            driver2_id: int,
            driver3_id: int,
            wildcard_id: int
    ) -> Tuple[bool, Optional[str], List[str]]:
        """
        Validate that no exhausted drivers are being drafted.
        Only checks drivers that are LOCKED IN (past their draft deadline).

        Returns:
            Tuple of (is_valid, error_message, list_of_exhausted_driver_names)
        """
        driver_ids = [driver1_id, driver2_id, driver3_id, wildcard_id]

        # Get exhausted drivers for this player in this league (from locked-in drafts only)
        exhausted_drivers = await self.exhaustion_repo.get_exhausted_drivers(player_id, league_id)
        exhausted_driver_ids = {ed.driver_id for ed in exhausted_drivers}

        # Check for conflicts
        conflicting_ids = [did for did in driver_ids if did in exhausted_driver_ids]

        if conflicting_ids:
            # Get driver names for error message
            driver_names = []
            for driver_id in conflicting_ids:
                driver = await self.driver_repo.get_driver_by_id(driver_id)
                if driver:
                    driver_names.append(f"{driver.first_name} {driver.last_name}")

            error_msg = (
                f"Cannot draft exhausted driver(s): {', '.join(driver_names)}. "
                f"These drivers were used in the previous 2 consecutive Grand Prix and must sit out this round."
            )
            return False, error_msg, driver_names

        return True, None, []

    async def validate_constructor_exhaustion(
            self,
            player_id: int,
            league_id: int,
            constructor_id: int
    ) -> Tuple[bool, Optional[str], List[str]]:
        """
        Validate that an exhausted constructor is not being drafted.
        Only checks constructors that are LOCKED IN (past their draft deadline).

        Returns:
            Tuple of (is_valid, error_message, list_of_exhausted_constructor_names)
        """
        # Get exhaustion status for this specific constructor
        exhaustion = await self.constructor_exhaustion_repo.get_constructor_exhaustion_status(
            player_id, league_id, constructor_id
        )

        if exhaustion and exhaustion.is_exhausted:
            constructor = await self.constructor_repo.get_constructor_by_id(constructor_id)
            constructor_name = constructor.full_name if constructor else f"Constructor ID {constructor_id}"

            error_msg = (
                f"Cannot draft exhausted constructor: {constructor_name}. "
                f"This constructor was used in the previous 2 consecutive Grand Prix and must sit out this round."
            )
            return False, error_msg, [constructor_name]

        return True, None, []

    async def validate_prospective_exhaustion(
            self,
            player_id: int,
            league_id: int,
            grand_prix_id: int,
            driver1_id: int,
            driver2_id: int,
            driver3_id: int,
            constructor_id: int,
            wildcard_id: int
    ) -> Tuple[bool, Optional[str], List[str]]:
        """
        Validate that no driver or constructor is being drafted for more than 2 consecutive GPs in advance.
        This checks prospective drafts (not yet locked in) to prevent illegal advance drafting.

        Returns:
            Tuple of (is_valid, error_message, list_of_violating_names)
        """
        driver_ids = [driver1_id, driver2_id, driver3_id, wildcard_id]

        # Get the current grand prix round number
        current_gp = await self.grand_prix_repo.get_grand_prix_by_id(grand_prix_id)
        if not current_gp:
            return False, "Grand Prix not found", []

        current_round = current_gp.round_number
        season_id = current_gp.season_id

        # Get all grands prix for the season, ordered by round
        all_gps = await self.grand_prix_repo.list_grands_prix_by_season(season_id)
        gp_map = {gp.round_number: gp for gp in all_gps}

        # Get all existing drafts for this player in this league for the season
        existing_drafts = await self.draft_repo.list_drafts_for_player_in_league(player_id, league_id)

        # Build a map of round_number -> drafted_driver_ids
        # and a map of round_number -> constructor_id
        drafts_by_round = {}
        constructor_by_round = {}
        for draft in existing_drafts:
            gp = await self.grand_prix_repo.get_grand_prix_by_id(draft.grand_prix_id)
            if gp and gp.season_id == season_id:
                drafts_by_round[gp.round_number] = [
                    draft.driver1_id,
                    draft.driver2_id,
                    draft.driver3_id,
                    draft.wildcard_id
                ]
                constructor_by_round[gp.round_number] = draft.constructor_id

        # Add the current draft being validated
        drafts_by_round[current_round] = driver_ids
        constructor_by_round[current_round] = constructor_id

        # Check each driver for consecutive usage
        violating_drivers = []
        for driver_id in driver_ids:
            consecutive_count = 0
            max_consecutive = 0

            # Scan through all rounds in order
            for round_num in sorted(drafts_by_round.keys()):
                if driver_id in drafts_by_round[round_num]:
                    consecutive_count += 1
                    max_consecutive = max(max_consecutive, consecutive_count)
                else:
                    consecutive_count = 0

            # Check if this driver would be used more than 2 consecutive times
            if max_consecutive > 2:
                driver = await self.driver_repo.get_driver_by_id(driver_id)
                if driver:
                    violating_drivers.append(f"{driver.first_name} {driver.last_name}")

        if violating_drivers:
            error_msg = (
                f"Cannot draft {', '.join(violating_drivers)} for more than 2 consecutive Grand Prix. "
                f"You have already drafted them for 2 consecutive races."
            )
            return False, error_msg, violating_drivers

        # Check constructor for consecutive usage
        consecutive_count = 0
        max_consecutive = 0

        for round_num in sorted(constructor_by_round.keys()):
            if constructor_by_round[round_num] == constructor_id:
                consecutive_count += 1
                max_consecutive = max(max_consecutive, consecutive_count)
            else:
                consecutive_count = 0

        if max_consecutive > 2:
            constructor = await self.constructor_repo.get_constructor_by_id(constructor_id)
            constructor_name = constructor.full_name if constructor else f"Constructor ID {constructor_id}"
            error_msg = (
                f"Cannot draft {constructor_name} for more than 2 consecutive Grand Prix. "
                f"You have already drafted them for 2 consecutive races."
            )
            return False, error_msg, [constructor_name]

        return True, None, []

    async def validate_counterpicks(
            self,
            player_id: int,
            league_id: int,
            grand_prix_id: int,
            driver1_id: int,
            driver2_id: int,
            driver3_id: int,
            wildcard_id: int
    ) -> Tuple[bool, Optional[str], List[str]]:
        """
        Validate that no counterpicked drivers are being drafted

        Returns:
            Tuple of (is_valid, error_message, list_of_counterpicked_driver_names)
        """
        driver_ids = [driver1_id, driver2_id, driver3_id, wildcard_id]

        # Get counterpicks targeting this player for this GP in this league
        counterpicks = await self.counterpick_repo.list_counterpicks_targeting_player(
            grand_prix_id=grand_prix_id,
            league_id=league_id,
            target_player_id=player_id
        )

        counterpicked_driver_ids = {cp.target_driver_id for cp in counterpicks}

        # Check for conflicts
        conflicting_ids = [did for did in driver_ids if did in counterpicked_driver_ids]

        if conflicting_ids:
            # Get driver names for error message
            driver_names = []
            for driver_id in conflicting_ids:
                driver = await self.driver_repo.get_driver_by_id(driver_id)
                if driver:
                    driver_names.append(f"{driver.first_name} {driver.last_name}")

            error_msg = (
                f"Cannot draft counterpicked driver(s): {', '.join(driver_names)}. "
                f"These drivers have been counterpicked against you for this Grand Prix."
            )
            return False, error_msg, driver_names

        return True, None, []

    async def get_available_drivers_for_player(
            self,
            player_id: int,
            league_id: int,
            grand_prix_id: int,
            season_id: int
    ) -> Dict[str, List[Driver]]:
        """
        Get lists of available and unavailable drivers for a player

        Returns:
            Dictionary with keys:
            - 'available': List of drivers that can be drafted
            - 'exhausted': List of exhausted drivers
            - 'counterpicked': List of counterpicked drivers
        """
        # Get all active drivers for the season
        all_drivers = await self.driver_repo.list_drivers_by_season(
            season_id=season_id,
            active_only=True
        )

        # Get exhausted drivers
        exhausted_records = await self.exhaustion_repo.get_exhausted_drivers(player_id, league_id)
        exhausted_driver_ids = {er.driver_id for er in exhausted_records}

        # Get counterpicked drivers
        counterpicks = await self.counterpick_repo.list_counterpicks_targeting_player(
            grand_prix_id=grand_prix_id,
            league_id=league_id,
            target_player_id=player_id
        )
        counterpicked_driver_ids = {cp.target_driver_id for cp in counterpicks}

        # Categorize drivers
        available = []
        exhausted = []
        counterpicked = []

        for driver in all_drivers:
            if driver.id in exhausted_driver_ids:
                exhausted.append(driver)
            elif driver.id in counterpicked_driver_ids:
                counterpicked.append(driver)
            else:
                available.append(driver)

        return {
            'available': available,
            'exhausted': exhausted,
            'counterpicked': counterpicked
        }

    async def submit_draft(
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
    ) -> Tuple[Optional[Draft], Optional[str]]:
        """
        Submit or update a draft with comprehensive validation

        Returns:
            Tuple of (Draft object or None, error_message or None)
        """
        try:
            # 1. Check draft deadline
            is_valid, error = await self.validate_draft_deadline(grand_prix_id)
            if not is_valid:
                return None, error

            # 2. Validate unique drivers
            is_valid, error = await self.validate_unique_drivers(
                driver1_id, driver2_id, driver3_id, wildcard_id
            )
            if not is_valid:
                return None, error

            # 3. Validate constructor representation
            is_valid, error = await self.validate_constructor_representation(
                driver1_id, driver2_id, driver3_id, wildcard_id, constructor_id
            )
            if not is_valid:
                return None, error

            # 4. Validate minimum constructors (3+)
            is_valid, error = await self.validate_minimum_constructors(
                driver1_id, driver2_id, driver3_id, wildcard_id
            )
            if not is_valid:
                return None, error

            # 5. Validate LOCKED-IN driver exhaustion (from past deadlines)
            is_valid, error, _ = await self.validate_driver_exhaustion(
                player_id, league_id, driver1_id, driver2_id, driver3_id, wildcard_id
            )
            if not is_valid:
                return None, error

            # 5b. Validate LOCKED-IN constructor exhaustion (from past deadlines)
            is_valid, error, _ = await self.validate_constructor_exhaustion(
                player_id, league_id, constructor_id
            )
            if not is_valid:
                return None, error

            # 6. Validate PROSPECTIVE exhaustion (no more than 2 consecutive in advance)
            is_valid, error, _ = await self.validate_prospective_exhaustion(
                player_id, league_id, grand_prix_id,
                driver1_id, driver2_id, driver3_id, wildcard_id
            )
            if not is_valid:
                return None, error

            # 7. Validate counterpicks
            is_valid, error, _ = await self.validate_counterpicks(
                player_id, league_id, grand_prix_id,
                driver1_id, driver2_id, driver3_id, wildcard_id
            )
            if not is_valid:
                return None, error

            # All validations passed - create/update draft
            draft = await self.draft_repo.create_draft(
                player_id=player_id,
                league_id=league_id,
                grand_prix_id=grand_prix_id,
                driver1_id=driver1_id,
                driver2_id=driver2_id,
                driver3_id=driver3_id,
                wildcard_id=wildcard_id,
                constructor_id=constructor_id,
                is_auto_assigned=is_auto_assigned
            )

            return draft, None

        except Exception as e:
            # Handle database-level validation errors (from triggers)
            error_msg = str(e)

            # Parse PostgreSQL errors for user-friendly messages
            if "At least one driver must belong to the selected constructor" in error_msg:
                return None, "At least one of your drafted drivers must belong to the selected constructor"
            elif "Draft must include drivers from at least 3 different constructors" in error_msg:
                return None, "Your 4 drivers must represent at least 3 different constructors"
            elif "Cannot draft exhausted driver" in error_msg:
                return None, error_msg
            elif "Cannot draft exhausted constructor" in error_msg:
                return None, error_msg
            elif "Cannot draft driver" in error_msg and "counterpicked" in error_msg:
                return None, error_msg
            else:
                return None, f"Draft submission failed: {error_msg}"

    async def get_draft_info(
            self,
            player_id: int,
            league_id: int,
            grand_prix_id: int
    ) -> Optional[Dict]:
        """
        Get comprehensive draft information including driver and constructor details

        Returns:
            Dictionary with draft details or None if no draft exists
        """
        draft = await self.draft_repo.get_draft(player_id, league_id, grand_prix_id)

        if not draft:
            return None

        # Get driver details
        driver1 = await self.driver_repo.get_driver_by_id(draft.driver1_id)
        driver2 = await self.driver_repo.get_driver_by_id(draft.driver2_id)
        driver3 = await self.driver_repo.get_driver_by_id(draft.driver3_id)
        wildcard = await self.driver_repo.get_driver_by_id(draft.wildcard_id)
        constructor = await self.constructor_repo.get_constructor_by_id(draft.constructor_id)

        return {
            'draft': draft,
            'driver1': driver1,
            'driver2': driver2,
            'driver3': driver3,
            'wildcard': wildcard,
            'constructor': constructor
        }