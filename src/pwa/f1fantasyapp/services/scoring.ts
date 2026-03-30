// services/scoring.ts
// This service calculates fantasy points based on race results and scoring rules

import pool from './db';

// Define TypeScript interfaces for type safety
// These describe the shape of our data

interface ScoringRules {
    race_points: number[];
    quali_points: number[];
    sprint_points: number[];
    sprint_quali_points: number[];
    constructor_points: number[];
    bogey_points: number[];
    bogey_points_sprint: number[];
}

interface Draft {
    player_id: number;
    league_id: number;
    grand_prix_id: number;
    driver1_id: number;
    driver2_id: number;
    driver3_id: number;
    wildcard_id: number;
    constructor_id: number;
}

interface RaceResult {
    driver_id: number;
    position: number;
    session_type: string;
    constructor_id?: number;
}

interface PointsBreakdown {
    driver1: { name: string; points: number; details: string };
    driver2: { name: string; points: number; details: string };
    driver3: { name: string; points: number; details: string };
    wildcard: { name: string; points: number; details: string };
    constructor: { name: string; points: number; details: string };
    total: number;
}

export class ScoringService {
    // Fetch the scoring rules for a specific season from the database
    async getScoringRules(seasonId: number): Promise<ScoringRules> {
        const query = `
      SELECT rule_key, rule_value 
      FROM scoring_rules 
      WHERE season_id = $1
    `;
        const result = await pool.query(query, [seasonId]);

        // Transform the database rows into a single object with all rules
        const rules: any = {};
        result.rows.forEach(row => {
            rules[row.rule_key] = row.rule_value;
        });

        return rules as ScoringRules;
    }

    // Calculate points for a specific driver based on their position
    calculateDriverPoints(
        position: number,
        sessionType: string,
        rules: ScoringRules
    ): number {
        // Position is 1-indexed (1st place, 2nd place, etc.)
        // Array is 0-indexed, so we subtract 1
        const index = position - 1;

        switch (sessionType) {
            case 'race':
                // For race: top 10 get points (if position <= 10 and within array bounds)
                return rules.race_points[index] || 0;
            case 'qualifying':
                // For qualifying: top 5 get points
                return rules.quali_points[index] || 0;
            case 'sprint':
                // Sprint has a different scoring system (can be negative!)
                return rules.sprint_points[index] || 0;
            case 'sprint_qualifying':
                // Sprint qualifying: top 3 get points
                return rules.sprint_quali_points[index] || 0;
            default:
                return 0;
        }
    }

    // Calculate points for a constructor based on their drivers' positions
    calculateConstructorPoints(
        constructorId: number,
        allRaceResults: RaceResult[],
        rules: ScoringRules
    ): number {
        // Get race results only
        const raceResults = allRaceResults.filter(r => r.session_type === 'race');

        // Group drivers by constructor and calculate total points for each constructor
        const constructorPointsMap = new Map<number, number>();

        for (const result of raceResults) {
            if (!result.constructor_id) continue;

            // Calculate points for this driver based on their finishing position
            const driverPoints = this.calculateDriverPoints(result.position, 'race', rules);

            // Add to constructor's total
            const currentTotal = constructorPointsMap.get(result.constructor_id) || 0;
            constructorPointsMap.set(result.constructor_id, currentTotal + driverPoints);
        }

        // Sort constructors by total points (descending)
        const rankedConstructors = Array.from(constructorPointsMap.entries())
            .sort((a, b) => b[1] - a[1]); // Sort by points, highest first

        // Find the ranking (position) of the requested constructor
        const constructorRank = rankedConstructors.findIndex((entry) => entry[0] === constructorId);

        // If constructor not found in results, return 0
        if (constructorRank === -1) {
            return 0;
        }

        // Award points based on constructor's ranking (1st place = index 0, etc.)
        return rules.constructor_points[constructorRank] || 0;
    }

    // Calculate "bogey" (wildcard) points based on position delta from teammate
    async calculateBogeyPoints(
        wildcardDriverId: number,
        sessionType: string,
        results: RaceResult[],
        rules: ScoringRules,
        client: any
    ): Promise<{ points: number; details: string }> {
        // Only calculate for race and sprint sessions
        if (sessionType !== 'race' && sessionType !== 'sprint') {
            return { points: 0, details: '' };
        }

        // Get the wildcard driver's constructor_id and position
        const wildcardResult = results.find(
            r => r.driver_id === wildcardDriverId && r.session_type === sessionType
        );

        if (!wildcardResult) {
            return { points: 0, details: 'No result' };
        }

        const wildcardConstructorId = wildcardResult.constructor_id;
        const wildcardPosition = wildcardResult.position;

        // Find the teammate (another active driver in the same constructor)
        const teammateQuery = await client.query(
            `SELECT id FROM drivers
             WHERE constructor_id = $1
               AND id != $2
               AND is_active = true
             LIMIT 1`,
            [wildcardConstructorId, wildcardDriverId]
        );

        if (teammateQuery.rows.length === 0) {
            return { points: 0, details: 'No teammate found' };
        }

        const teammateId = teammateQuery.rows[0].id;

        // Find the teammate's position in this session
        const teammateResult = results.find(
            r => r.driver_id === teammateId && r.session_type === sessionType
        );

        if (!teammateResult) {
            return { points: 0, details: 'Teammate did not finish' };
        }

        const teammatePosition = teammateResult.position;

        // Calculate position delta: positive means wildcard finished ahead
        const positionDelta = teammatePosition - wildcardPosition;

        // Get points from the scoring rules based on absolute delta
        const absPositionDelta = Math.abs(positionDelta);
        const pointsArray = sessionType === 'sprint' ? rules.bogey_points_sprint : rules.bogey_points;
        const basePoints = pointsArray[absPositionDelta] || 0;

        // If position delta is negative (finished behind teammate), make points negative
        const finalPoints = positionDelta < 0 ? -basePoints : basePoints;

        const details = `P${wildcardPosition} vs teammate P${teammatePosition} (Δ${positionDelta > 0 ? '+' : ''}${positionDelta}, ${finalPoints}pts)`;

        return { points: finalPoints, details };
    }

    // Main function to calculate points for all players in a league for a specific GP
    async calculatePointsForGrandPrix(
        grandPrixId: number,
        leagueId: number
    ): Promise<void> {
        // Start a database transaction - if anything fails, all changes are rolled back
        const client = await pool.connect();

        try {
            await client.query('BEGIN');

            // 1. Get the season ID for this Grand Prix
            const seasonResult = await client.query(
                'SELECT season_id FROM grands_prix WHERE id = $1',
                [grandPrixId]
            );
            const seasonId = seasonResult.rows[0].season_id;

            // 2. Fetch scoring rules for this season
            const rules = await this.getScoringRules(seasonId);

            // 3. Get all players in this league
            const playersResult = await client.query(
                `SELECT player_id FROM player_leagues WHERE league_id = $1`,
                [leagueId]
            );

            // 4. Check for missing drafts and generate them
            for (const player of playersResult.rows) {
                const draftCheck = await client.query(
                    `SELECT id FROM drafts 
                     WHERE player_id = $1 AND league_id = $2 AND grand_prix_id = $3`,
                    [player.player_id, leagueId, grandPrixId]
                );

                if (draftCheck.rows.length === 0) {
                    // Player hasn't submitted a draft - generate one automatically
                    await this.generateAutoDraft(player.player_id, leagueId, grandPrixId, seasonId, client);
                }
            }

            // 5. Get all drafts for this GP in this league (including auto-generated ones)
            const draftsResult = await client.query(
                `SELECT * FROM drafts 
                 WHERE grand_prix_id = $1 AND league_id = $2`,
                [grandPrixId, leagueId]
            );

            // 6. Get all race results for this GP
            const resultsQuery = `
                SELECT rr.*, d.constructor_id
                FROM race_results rr
                         JOIN drivers d ON d.id = rr.driver_id
                WHERE rr.grand_prix_id = $1
            `;
            const resultsResult = await client.query(resultsQuery, [grandPrixId]);
            const results: RaceResult[] = resultsResult.rows;

            // 7. Calculate points for each player's draft
            for (const draft of draftsResult.rows) {
                const breakdown = await this.calculatePlayerPoints(
                    draft,
                    results,
                    rules,
                    client
                );

                // 8. Store the calculated points in player_round_scores table
                await client.query(
                    `INSERT INTO player_round_scores
                     (player_id, league_id, grand_prix_id, total_points, breakdown_json, calculated_at)
                     VALUES ($1, $2, $3, $4, $5, NOW())
                     ON CONFLICT (player_id, league_id, grand_prix_id)
                         DO UPDATE SET
                                       total_points = $4,
                                       breakdown_json = $5,
                                       calculated_at = NOW()`,
                    [
                        draft.player_id,
                        draft.league_id,
                        draft.grand_prix_id,
                        breakdown.total,
                        JSON.stringify(breakdown)
                    ]
                );

                // 9. Update driver exhaustion tracking
                await this.updateDriverExhaustion(draft, client);

                // 10. Update constructor exhaustion tracking
                await this.updateConstructorExhaustion(draft, client);
            }

            // 11. Mark the Grand Prix as completed
            await client.query(
                'UPDATE grands_prix SET is_completed = TRUE WHERE id = $1',
                [grandPrixId]
            );

            // Commit all changes to the database
            await client.query('COMMIT');
        } catch (error) {
            // If anything goes wrong, undo all changes
            await client.query('ROLLBACK');
            throw error;
        } finally {
            // Always release the database connection back to the pool
            client.release();
        }
    }

    // Generate an automatic draft for a player based on their previous draft
    private async generateAutoDraft(
        playerId: number,
        leagueId: number,
        grandPrixId: number,
        seasonId: number,
        client: any
    ): Promise<void> {
        // Get previous draft from the same league (most recent)
        const previousDraftResult = await client.query(
            `SELECT driver1_id, driver2_id, driver3_id, wildcard_id, constructor_id
             FROM drafts
             WHERE player_id = $1 AND league_id = $2 AND grand_prix_id != $3
             ORDER BY grand_prix_id DESC
             LIMIT 1`,
            [playerId, leagueId, grandPrixId]
        );

        // Get all active drivers for this season
        const activeDriversResult = await client.query(
            `SELECT id, constructor_id FROM drivers 
             WHERE season_id = $1 AND is_active = TRUE`,
            [seasonId]
        );

        const activeDrivers = activeDriversResult.rows;

        // Get exhausted drivers for this player
        const exhaustedDriversResult = await client.query(
            `SELECT driver_id FROM driver_exhaustion
             WHERE player_id = $1 AND league_id = $2 AND is_exhausted = TRUE`,
            [playerId, leagueId]
        );

        const exhaustedDriverIds = exhaustedDriversResult.rows.map(r => r.driver_id);

        // Get all constructors for this season
        const constructorsResult = await client.query(
            `SELECT id FROM constructors WHERE season_id = $1`,
            [seasonId]
        );

        const constructorIds = constructorsResult.rows.map(r => r.id);

        let draft: {
            driver1_id: number;
            driver2_id: number;
            driver3_id: number;
            wildcard_id: number;
            constructor_id: number;
        } | null = null;

        let attempts = 0;
        const maxAttempts = 100;

        // Keep trying to generate a valid draft
        while (!draft && attempts < maxAttempts) {
            attempts++;

            const selectedDrivers = await this.selectWeightedRandomDrivers(
                activeDrivers,
                exhaustedDriverIds,
                previousDraftResult.rows[0],
                constructorIds
            );

            if (selectedDrivers) {
                // Validate the draft meets all requirements
                const isValid = await this.validateAutoDraft(
                    selectedDrivers,
                    exhaustedDriverIds,
                    activeDrivers
                );

                if (isValid) {
                    draft = selectedDrivers;
                }
            }
        }

        if (!draft) {
            throw new Error(`Failed to generate valid auto-draft for player ${playerId} after ${maxAttempts} attempts`);
        }

        // Insert the auto-generated draft
        await client.query(
            `INSERT INTO drafts 
             (player_id, league_id, grand_prix_id, driver1_id, driver2_id, driver3_id, wildcard_id, constructor_id, is_auto_assigned, updated_at)
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8, TRUE, NOW())`,
            [
                playerId,
                leagueId,
                grandPrixId,
                draft.driver1_id,
                draft.driver2_id,
                draft.driver3_id,
                draft.wildcard_id,
                draft.constructor_id
            ]
        );
    }

    // Select weighted random drivers based on previous draft preferences
    private async selectWeightedRandomDrivers(
        activeDrivers: Array<{ id: number; constructor_id: number }>,
        exhaustedDriverIds: number[],
        previousDraft: any,
        constructorIds: number[]
    ): Promise<{
        driver1_id: number;
        driver2_id: number;
        driver3_id: number;
        wildcard_id: number;
        constructor_id: number;
    } | null> {
        // Filter out exhausted drivers
        const availableDrivers = activeDrivers.filter(
            d => !exhaustedDriverIds.includes(d.id)
        );

        if (availableDrivers.length < 4) {
            return null; // Not enough drivers available
        }

        // Create weighted selection based on previous draft
        const previousDriverIds = previousDraft
            ? [
                previousDraft.driver1_id,
                previousDraft.driver2_id,
                previousDraft.driver3_id,
                previousDraft.wildcard_id
            ]
            : [];

        // Assign weights: previous drivers get 2x weight, others get 1x
        const weightedDrivers = availableDrivers.map(d => ({
            ...d,
            weight: previousDriverIds.includes(d.id) ? 2 : 1
        }));

        // Weighted random selection
        const selectWeightedRandom = (pool: typeof weightedDrivers) => {
            const totalWeight = pool.reduce((sum, d) => sum + d.weight, 0);
            let random = Math.random() * totalWeight;

            for (const driver of pool) {
                random -= driver.weight;
                if (random <= 0) {
                    return driver;
                }
            }

            return pool[pool.length - 1];
        };

        // Select 4 unique drivers
        const selectedDrivers: number[] = [];
        let pool = [...weightedDrivers];

        for (let i = 0; i < 4; i++) {
            if (pool.length === 0) return null;

            const selected = selectWeightedRandom(pool);
            selectedDrivers.push(selected.id);

            // Remove selected driver from pool
            pool = pool.filter(d => d.id !== selected.id);
        }

        // Select constructor (prefer previous constructor, but random if none)
        let constructorId: number;
        if (previousDraft?.constructor_id && constructorIds.includes(previousDraft.constructor_id)) {
            // 70% chance to keep previous constructor
            constructorId = Math.random() < 0.7
                ? previousDraft.constructor_id
                : constructorIds[Math.floor(Math.random() * constructorIds.length)];
        } else {
            constructorId = constructorIds[Math.floor(Math.random() * constructorIds.length)];
        }

        return {
            driver1_id: selectedDrivers[0],
            driver2_id: selectedDrivers[1],
            driver3_id: selectedDrivers[2],
            wildcard_id: selectedDrivers[3],
            constructor_id: constructorId
        };
    }

    // Validate that the auto-generated draft meets all requirements
    private async validateAutoDraft(
        draft: {
            driver1_id: number;
            driver2_id: number;
            driver3_id: number;
            wildcard_id: number;
            constructor_id: number;
        },
        exhaustedDriverIds: number[],
        activeDrivers: Array<{ id: number; constructor_id: number }>
    ): Promise<boolean> {
        const driverIds = [draft.driver1_id, draft.driver2_id, draft.driver3_id, draft.wildcard_id];

        // Check 1: All drivers must be unique
        const uniqueDrivers = new Set(driverIds);
        if (uniqueDrivers.size !== 4) {
            return false;
        }

        // Check 2: No exhausted drivers
        for (const driverId of driverIds) {
            if (exhaustedDriverIds.includes(driverId)) {
                return false;
            }
        }

        // Check 3: At least 3 different constructors
        const constructorIds = driverIds.map(driverId => {
            const driver = activeDrivers.find(d => d.id === driverId);
            return driver?.constructor_id;
        });

        const uniqueConstructors = new Set(constructorIds.filter(Boolean));
        if (uniqueConstructors.size < 3) {
            return false;
        }

        // Check 4: At least one driver from the selected constructor
        const hasConstructorDriver = driverIds.some(driverId => {
            const driver = activeDrivers.find(d => d.id === driverId);
            return driver?.constructor_id === draft.constructor_id;
        });

        if (!hasConstructorDriver) {
            return false;
        }

        return true;
    }

    // Calculate points for a single player's draft
    private async calculatePlayerPoints(
        draft: Draft,
        results: RaceResult[],
        rules: ScoringRules,
        client: any
    ): Promise<PointsBreakdown> {
        // Helper function to get driver details
        const getDriverInfo = async (driverId: number) => {
            const res = await client.query(
                'SELECT first_name, last_name, code FROM drivers WHERE id = $1',
                [driverId]
            );
            return res.rows[0];
        };

        const getConstructorInfo = async (constructorId: number) => {
            const res = await client.query(
                'SELECT full_name FROM constructors WHERE id = $1',
                [constructorId]
            );
            return res.rows[0];
        };

        // Initialize the breakdown object
        const breakdown: PointsBreakdown = {
            driver1: { name: '', points: 0, details: '' },
            driver2: { name: '', points: 0, details: '' },
            driver3: { name: '', points: 0, details: '' },
            wildcard: { name: '', points: 0, details: '' },
            constructor: { name: '', points: 0, details: '' },
            total: 0
        };

        // Calculate points for each of the 3 main drivers
        for (const [key, driverId] of [
            ['driver1', draft.driver1_id],
            ['driver2', draft.driver2_id],
            ['driver3', draft.driver3_id]
        ] as const) {
            const driverInfo = await getDriverInfo(driverId);
            const driverResults = results.filter(r => r.driver_id === driverId);

            let driverPoints = 0;
            const details: string[] = [];

            // Add up points from all sessions (quali, race, sprint, etc.)
            for (const result of driverResults) {
                const points = this.calculateDriverPoints(
                    result.position,
                    result.session_type,
                    rules
                );
                driverPoints += points;
                details.push(`${result.session_type}: P${result.position} (${points}pts)`);
            }

            breakdown[key] = {
                name: `${driverInfo.first_name} ${driverInfo.last_name}`,
                points: driverPoints,
                details: details.join(', ')
            };
            breakdown.total += driverPoints;
        }

        // Calculate wildcard (bogey) driver points
        const wildcardInfo = await getDriverInfo(draft.wildcard_id);
        let wildcardPoints = 0;
        const wildcardDetails: string[] = [];

        // Process race results
        const raceResult = results.find(
            r => r.driver_id === draft.wildcard_id && r.session_type === 'race'
        );
        if (raceResult) {
            const { points, details } = await this.calculateBogeyPoints(
                draft.wildcard_id,
                'race',
                results,
                rules,
                client
            );
            wildcardPoints += points;
            if (details) wildcardDetails.push(`race: ${details}`);
        }

/*        // Process sprint results
        const sprintResult = results.find(
            r => r.driver_id === draft.wildcard_id && r.session_type === 'sprint'
        );
        if (sprintResult) {
            const { points, details } = await this.calculateBogeyPoints(
                draft.wildcard_id,
                'sprint',
                results,
                rules,
                client
            );
            wildcardPoints += points;
            if (details) wildcardDetails.push(`sprint: ${details}`);
        }*/

        breakdown.wildcard = {
            name: `${wildcardInfo.first_name} ${wildcardInfo.last_name}`,
            points: wildcardPoints,
            details: wildcardDetails.join(', ') || 'No results'
        };
        breakdown.total += wildcardPoints;

        // Calculate constructor points
        const constructorInfo = await getConstructorInfo(draft.constructor_id);
        const constructorPoints = this.calculateConstructorPoints(
            draft.constructor_id,
            results,
            rules
        );

        // Get constructor details - find drivers and their points
        const raceResults = results.filter(r => r.session_type === 'race');
        const constructorDrivers = raceResults.filter(r => r.constructor_id === draft.constructor_id);

        let constructorDetails = '';
        if (constructorDrivers.length > 0) {
            // Get constructor rank
            const constructorPointsMap = new Map<number, number>();
            for (const result of raceResults) {
                if (!result.constructor_id) continue;
                const driverPoints = this.calculateDriverPoints(result.position, 'race', rules);
                const currentTotal = constructorPointsMap.get(result.constructor_id) || 0;
                constructorPointsMap.set(result.constructor_id, currentTotal + driverPoints);
            }

            const rankedConstructors = Array.from(constructorPointsMap.entries())
                .sort((a, b) => b[1] - a[1]);
            const constructorRank = rankedConstructors.findIndex((entry) => entry[0] === draft.constructor_id) + 1;

            // Get driver names and points
            const driverDetailsPromises = constructorDrivers.map(async (cd) => {
                const driverInfo = await getDriverInfo(cd.driver_id);
                const points = this.calculateDriverPoints(cd.position, 'race', rules);
                return {
                    name: `${driverInfo.first_name} ${driverInfo.last_name}`,
                    points
                };
            });

            const driverDetails = await Promise.all(driverDetailsPromises);
            const totalConstructorRacePoints = driverDetails.reduce((sum, d) => sum + d.points, 0);

            if (driverDetails.length >= 2) {
                constructorDetails = `${driverDetails[0].name} scored ${driverDetails[0].points} points and ${driverDetails[1].name} scored ${driverDetails[1].points} points for a total of ${totalConstructorRacePoints} points. Constructor rank is ${constructorRank}.`;
            } else if (driverDetails.length === 1) {
                constructorDetails = `${driverDetails[0].name} scored ${driverDetails[0].points} points for a total of ${driverDetails[0].points} points. Constructor rank is ${constructorRank}.`;
            }
        } else {
            constructorDetails = 'No results';
        }

        breakdown.constructor = {
            name: constructorInfo.full_name,
            points: constructorPoints,
            details: constructorDetails
        };
        breakdown.total += constructorPoints;

        return breakdown;
    }

    // Update driver exhaustion status after calculating points
    private async updateDriverExhaustion(draft: Draft, client: any): Promise<void> {
        const driverIds = [
            draft.driver1_id,
            draft.driver2_id,
            draft.driver3_id,
            draft.wildcard_id
        ];

        // Get the current GP's round number
        const gpResult = await client.query(
            'SELECT round_number FROM grands_prix WHERE id = $1',
            [draft.grand_prix_id]
        );
        const currentRound = gpResult.rows[0].round_number;

        // Get previous GP
        const prevGpResult = await client.query(
            `SELECT id FROM grands_prix 
       WHERE season_id = (SELECT season_id FROM grands_prix WHERE id = $1)
       AND round_number = $2`,
            [draft.grand_prix_id, currentRound - 1]
        );

        if (prevGpResult.rows.length === 0) {
            // First GP of season - initialize exhaustion tracking
            for (const driverId of driverIds) {
                await client.query(
                    `INSERT INTO driver_exhaustion 
           (player_id, league_id, driver_id, last_grand_prix_id, consecutive_uses, is_exhausted)
           VALUES ($1, $2, $3, $4, 1, FALSE)
           ON CONFLICT (player_id, league_id, driver_id)
           DO UPDATE SET 
             consecutive_uses = 1,
             is_exhausted = FALSE,
             last_grand_prix_id = $4,
             updated_at = NOW()`,
                    [draft.player_id, draft.league_id, driverId, draft.grand_prix_id]
                );
            }
            return;
        }

        const prevGpId = prevGpResult.rows[0].id;

        // Check which drivers were used in previous GP
        const prevDraftResult = await client.query(
            `SELECT driver1_id, driver2_id, driver3_id, wildcard_id
       FROM drafts
       WHERE player_id = $1 AND league_id = $2 AND grand_prix_id = $3`,
            [draft.player_id, draft.league_id, prevGpId]
        );

        if (prevDraftResult.rows.length > 0) {
            const prevDriverIds = [
                prevDraftResult.rows[0].driver1_id,
                prevDraftResult.rows[0].driver2_id,
                prevDraftResult.rows[0].driver3_id,
                prevDraftResult.rows[0].wildcard_id
            ];

            for (const driverId of driverIds) {
                const wasUsedBefore = prevDriverIds.includes(driverId);

                await client.query(
                    `INSERT INTO driver_exhaustion 
           (player_id, league_id, driver_id, last_grand_prix_id, consecutive_uses, is_exhausted)
           VALUES ($1, $2, $3, $4, $5, $6)
           ON CONFLICT (player_id, league_id, driver_id)
           DO UPDATE SET 
             consecutive_uses = $5,
             is_exhausted = $6,
             last_grand_prix_id = $4,
             updated_at = NOW()`,
                    [
                        draft.player_id,
                        draft.league_id,
                        driverId,
                        draft.grand_prix_id,
                        wasUsedBefore ? 2 : 1,
                        wasUsedBefore // Exhausted if used 2 GPs in a row
                    ]
                );
            }
        }
    }

    // Update constructor exhaustion status after calculating points
    private async updateConstructorExhaustion(draft: Draft, client: any): Promise<void> {
        const constructorId = draft.constructor_id;

        // Get the current GP's round number
        const gpResult = await client.query(
            'SELECT round_number FROM grands_prix WHERE id = $1',
            [draft.grand_prix_id]
        );
        const currentRound = gpResult.rows[0].round_number;

        // Get previous GP
        const prevGpResult = await client.query(
            `SELECT id FROM grands_prix 
       WHERE season_id = (SELECT season_id FROM grands_prix WHERE id = $1)
       AND round_number = $2`,
            [draft.grand_prix_id, currentRound - 1]
        );

        if (prevGpResult.rows.length === 0) {
            // First GP of season - initialize exhaustion tracking
            await client.query(`INSERT INTO constructor_exhaustion 
           (player_id, league_id, constructor_id, last_grand_prix_id, consecutive_uses, is_exhausted)
           VALUES ($1, $2, $3, $4, 1, FALSE)
           ON CONFLICT (player_id, league_id, constructor_id)
           DO UPDATE SET 
             consecutive_uses = 1,
             is_exhausted = FALSE,
             last_grand_prix_id = $4,
             updated_at = NOW()`,
                    [draft.player_id, draft.league_id, constructorId, draft.grand_prix_id]
                );
            return;
        }

        const prevGpId = prevGpResult.rows[0].id;

        // Check which constructor was used in previous GP
        const prevDraftResult = await client.query(
            `SELECT constructor_id FROM drafts WHERE player_id = $1 AND league_id = $2 AND grand_prix_id = $3`,
            [draft.player_id, draft.league_id, prevGpId]
        );

        if (prevDraftResult.rows.length > 0) {
            const prevConstructorId = prevDraftResult.rows[0].constructor_id;

            const wasUsedBefore = prevConstructorId === constructorId;

            await client.query(
                `INSERT INTO constructor_exhaustion 
       (player_id, league_id, constructor_id, last_grand_prix_id, consecutive_uses, is_exhausted)
       VALUES ($1, $2, $3, $4, $5, $6)
       ON CONFLICT (player_id, league_id, constructor_id)
       DO UPDATE SET 
         consecutive_uses = $5,
         is_exhausted = $6,
         last_grand_prix_id = $4,
         updated_at = NOW()`,
                [
                    draft.player_id,
                    draft.league_id,
                    constructorId,
                    draft.grand_prix_id,
                    wasUsedBefore ? 2 : 1,
                    wasUsedBefore // Exhausted if used 2 GPs in a row
                ]
            );
        }
    }
}

export default new ScoringService();