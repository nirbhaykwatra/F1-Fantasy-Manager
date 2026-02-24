
-- ============================================================
-- LVS F1 Fantasy League — PostgreSQL Schema
-- Designed for multi-client access (Discord bot, PWA, APIs)
-- Supports players in multiple leagues with league-specific drafts
-- ============================================================

-- Enable UUID support (optional, for future use)
-- CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ------------------------------------------------------------
-- SEASONS
-- ------------------------------------------------------------
CREATE TABLE seasons (
    id          INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    year        SMALLINT NOT NULL UNIQUE,
    is_active   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_seasons_active ON seasons (is_active) WHERE is_active = TRUE;

COMMENT ON TABLE seasons IS 'F1 seasons (e.g., 2024, 2025)';
COMMENT ON COLUMN seasons.is_active IS 'Only one season can be active at a time';

-- ------------------------------------------------------------
-- CONSTRUCTORS (teams)
-- One row per constructor per season (names/colors can change)
-- ------------------------------------------------------------
CREATE TABLE constructors (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    season_id       INT NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    short_name      TEXT NOT NULL,                          -- e.g. 'mclaren'
    full_name       TEXT NOT NULL,                          -- e.g. 'McLaren Formula 1 Team'
    color_hex       CHAR(7) NOT NULL DEFAULT '#FFFFFF',     -- e.g. '#CC6600'
    ergast_id       TEXT,                                   -- for API lookups
    UNIQUE (season_id, short_name)
);

CREATE INDEX idx_constructors_season ON constructors (season_id);

COMMENT ON TABLE constructors IS 'F1 teams/constructors per season';

-- ------------------------------------------------------------
-- DRIVERS
-- One row per driver per season (handles mid-season team changes)
-- ------------------------------------------------------------
CREATE TABLE drivers (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    season_id       INT NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    code            CHAR(3) NOT NULL,                       -- e.g. 'VER'
    number          SMALLINT NOT NULL,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    constructor_id  INT NOT NULL REFERENCES constructors(id) ON DELETE CASCADE,
    ergast_id       TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,          -- false = excluded/reserve driver
    UNIQUE (season_id, code, number)
);

CREATE INDEX idx_drivers_season ON drivers (season_id);
CREATE INDEX idx_drivers_constructor ON drivers (constructor_id);

COMMENT ON TABLE drivers IS 'F1 drivers per season';
COMMENT ON COLUMN drivers.is_active IS 'Inactive drivers are excluded from drafts';

-- ------------------------------------------------------------
-- GRANDS PRIX (events in a season)
-- ------------------------------------------------------------
CREATE TABLE grands_prix (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    season_id       INT NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    round_number    SMALLINT NOT NULL,
    event_name      TEXT NOT NULL,
    circuit_key     TEXT,                                    -- e.g. 'silverstone'
    event_format    TEXT NOT NULL DEFAULT 'conventional',    -- 'conventional' | 'sprint_qualifying'
    quali_date_utc      TIMESTAMPTZ,
    sprint_quali_date_utc TIMESTAMPTZ,
    sprint_date_utc     TIMESTAMPTZ,
    race_date_utc       TIMESTAMPTZ,
    draft_deadline_utc  TIMESTAMPTZ,
    draft_reset_utc     TIMESTAMPTZ,
    counterpick_deadline_utc TIMESTAMPTZ,
    is_completed    BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (season_id, round_number)
);

CREATE INDEX idx_grands_prix_season ON grands_prix (season_id);
CREATE INDEX idx_grands_prix_completed ON grands_prix (season_id, is_completed);

COMMENT ON TABLE grands_prix IS 'Grand Prix events in a season';

-- ------------------------------------------------------------
-- LEAGUES (support multiple leagues per guild/season)
-- ------------------------------------------------------------
CREATE TABLE leagues (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name            TEXT NOT NULL,
    discord_guild_id BIGINT,                                -- NULL if non-Discord client
    season_id       INT NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    embed_color     INT NOT NULL DEFAULT 15135274,          -- 0xE8272A in decimal
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (discord_guild_id, name),                        -- No duplicate league names per guild
    UNIQUE (season_id, name)                                -- No duplicate league names per season
);

CREATE INDEX idx_leagues_discord_guild ON leagues (discord_guild_id);
CREATE INDEX idx_leagues_season ON leagues (season_id);

COMMENT ON TABLE leagues IS 'Fantasy leagues - multiple allowed per guild/season';
COMMENT ON COLUMN leagues.discord_guild_id IS 'NULL for non-Discord clients (PWA, API)';

-- ------------------------------------------------------------
-- PLAYERS (users who can join multiple leagues)
-- ------------------------------------------------------------
CREATE TABLE players (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    discord_user_id BIGINT UNIQUE,                          -- NULL if non-Discord
    username        TEXT NOT NULL UNIQUE,
    password        VARCHAR(255),                           -- bcrypt hash, NULL if Discord-only
    timezone        TEXT NOT NULL DEFAULT 'UTC',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_players_discord_user ON players (discord_user_id);
CREATE INDEX idx_players_username ON players (username);

COMMENT ON TABLE players IS 'Players/users who can participate in multiple leagues';
COMMENT ON COLUMN players.discord_user_id IS 'NULL for PWA-only users';
COMMENT ON COLUMN players.password IS 'NULL for Discord-only users';

-- ------------------------------------------------------------
-- PLAYER_LEAGUES (many-to-many junction table)
-- Links players to the leagues they participate in
-- ------------------------------------------------------------
CREATE TABLE player_leagues (
    player_id       INT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    league_id       INT NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    team_name       TEXT,
    team_motto      TEXT,
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (player_id, league_id)
);

CREATE INDEX idx_player_leagues_player ON player_leagues (player_id);
CREATE INDEX idx_player_leagues_league ON player_leagues (league_id);

COMMENT ON TABLE player_leagues IS 'Junction table for many-to-many player-league relationship';

-- ------------------------------------------------------------
-- DRAFTS (one per player per league per GP)
-- League-specific: players can have different drafts in different leagues
-- ------------------------------------------------------------
CREATE TABLE drafts (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    player_id       INT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    league_id       INT NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    grand_prix_id   INT NOT NULL REFERENCES grands_prix(id) ON DELETE CASCADE,
    driver1_id      INT NOT NULL REFERENCES drivers(id),
    driver2_id      INT NOT NULL REFERENCES drivers(id),
    driver3_id      INT NOT NULL REFERENCES drivers(id),
    wildcard_id     INT NOT NULL REFERENCES drivers(id),     -- "bogey" driver
    constructor_id  INT NOT NULL REFERENCES constructors(id),
    is_auto_assigned BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (player_id, league_id, grand_prix_id),
    CHECK (driver1_id != driver2_id
       AND driver1_id != driver3_id
       AND driver1_id != wildcard_id
       AND driver2_id != driver3_id
       AND driver2_id != wildcard_id
       AND driver3_id != wildcard_id)
);

CREATE INDEX idx_drafts_player_league ON drafts (player_id, league_id);
CREATE INDEX idx_drafts_grand_prix_league ON drafts (grand_prix_id, league_id);

COMMENT ON TABLE drafts IS 'Player draft selections per Grand Prix per league - allows different teams in different leagues';
COMMENT ON COLUMN drafts.wildcard_id IS 'The "bogey" driver (scores points based on position in the top 10 - can be negative)';

-- ------------------------------------------------------------
-- COUNTERPICKS (driver bans) - League-specific
-- ------------------------------------------------------------
CREATE TABLE counterpicks (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    grand_prix_id   INT NOT NULL REFERENCES grands_prix(id) ON DELETE CASCADE,
    league_id       INT NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    picking_player_id   INT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    target_player_id    INT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    target_driver_id    INT NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One counterpick per picking player per GP per league
    UNIQUE (grand_prix_id, league_id, picking_player_id),

    -- Can't counterpick yourself
    CHECK (picking_player_id != target_player_id)
);

CREATE INDEX idx_counterpicks_grand_prix_league ON counterpicks (grand_prix_id, league_id);
CREATE INDEX idx_counterpicks_target ON counterpicks (grand_prix_id, league_id, target_player_id);

COMMENT ON TABLE counterpicks IS 'Driver bans - one per player per Grand Prix per league';

-- ------------------------------------------------------------
-- RACE RESULTS (official finishing positions per session)
-- ------------------------------------------------------------
CREATE TABLE race_results (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    grand_prix_id   INT NOT NULL REFERENCES grands_prix(id) ON DELETE CASCADE,
    session_type    TEXT NOT NULL,    -- 'qualifying' | 'race' | 'sprint' | 'sprint_qualifying'
    driver_id       INT NOT NULL REFERENCES drivers(id),
    position        SMALLINT NOT NULL,
    UNIQUE (grand_prix_id, session_type, driver_id),
    CHECK (session_type IN ('qualifying', 'race', 'sprint', 'sprint_qualifying'))
);

CREATE INDEX idx_race_results_gp_session ON race_results (grand_prix_id, session_type);

COMMENT ON TABLE race_results IS 'Official F1 session results';

-- ------------------------------------------------------------
-- PLAYER ROUND SCORES (calculated fantasy points per GP per league)
-- League-specific: same player can have different scores in different leagues based on different drafts
-- ------------------------------------------------------------
CREATE TABLE player_round_scores (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    player_id       INT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    league_id       INT NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    grand_prix_id   INT NOT NULL REFERENCES grands_prix(id) ON DELETE CASCADE,
    total_points    INT NOT NULL DEFAULT 0,
    breakdown_json  JSONB NOT NULL DEFAULT '{}',             -- detailed scoring breakdown
    calculated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (player_id, league_id, grand_prix_id)
);

CREATE INDEX idx_player_scores_player_league ON player_round_scores (player_id, league_id);
CREATE INDEX idx_player_scores_gp_league ON player_round_scores (grand_prix_id, league_id);

COMMENT ON TABLE player_round_scores IS 'Calculated fantasy points per player per Grand Prix per league';

-- ------------------------------------------------------------
-- SCORING RULES (configurable per season)
-- ------------------------------------------------------------
CREATE TABLE scoring_rules (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    season_id       INT NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    rule_key        TEXT NOT NULL,    -- e.g. 'race_points', 'quali_points'
    rule_value      JSONB NOT NULL,   -- e.g. [25,18,15,12,10,8,6,4,2,1]
    UNIQUE (season_id, rule_key)
);

CREATE INDEX idx_scoring_rules_season ON scoring_rules (season_id);

COMMENT ON TABLE scoring_rules IS 'Configurable scoring rules per season';

-- Seed default scoring rules for a season (example)
-- INSERT INTO scoring_rules (season_id, rule_key, rule_value) VALUES
--   (1, 'race_points',          '[25,18,15,12,10,8,6,4,2,1]'),
--   (1, 'quali_points',         '[5,4,3,2,1]'),
--   (1, 'sprint_points',        '[5,4,3,2,1,-1,-2,-3,-4,-5]'),
--   (1, 'sprint_quali_points',  '[3,2,1]'),
--   (1, 'constructor_points',   '[5,4,3,2,1]'),
--   (1, 'bogey_points',         '[0,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10]'),
--   (1, 'bogey_points_sprint',  '[0,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,7]'),
--   (1, 'counterpick_limit',    '3'),
--   (1, 'driver_ban_limit',     '2');

-- ------------------------------------------------------------
-- VIEWS (convenient for dashboards and PWAs)
-- ------------------------------------------------------------

-- League-specific leaderboard view (season total)
CREATE OR REPLACE VIEW v_league_leaderboard AS
SELECT
    pl.league_id,
    l.name AS league_name,
    l.season_id,
    p.id AS player_id,
    p.username,
    pl.team_name,  -- Changed from p.team_name
    COALESCE(SUM(prs.total_points), 0) AS total_points,
    COUNT(DISTINCT prs.grand_prix_id) AS rounds_played,
    RANK() OVER (PARTITION BY pl.league_id ORDER BY COALESCE(SUM(prs.total_points), 0) DESC) AS rank
FROM player_leagues pl
JOIN players p ON p.id = pl.player_id
JOIN leagues l ON l.id = pl.league_id
LEFT JOIN player_round_scores prs ON prs.player_id = p.id AND prs.league_id = pl.league_id
LEFT JOIN grands_prix gp ON gp.id = prs.grand_prix_id AND gp.season_id = l.season_id
GROUP BY pl.league_id, l.name, l.season_id, p.id, p.username, pl.team_name
ORDER BY pl.league_id, total_points DESC;

COMMENT ON VIEW v_league_leaderboard IS 'Season standings per league with rankings';

-- Grand Prix leaderboard view (filtered by league)
CREATE OR REPLACE VIEW v_grand_prix_leaderboard AS
SELECT
    prs.league_id,
    l.name AS league_name,
    gp.id AS grand_prix_id,
    gp.event_name,
    gp.round_number,
    p.id AS player_id,
    p.username,
    pl.team_name,  -- Changed from p.team_name
    prs.total_points,
    prs.breakdown_json,
    RANK() OVER (PARTITION BY prs.league_id, gp.id ORDER BY prs.total_points DESC) AS rank
FROM player_round_scores prs
JOIN players p ON p.id = prs.player_id
JOIN player_leagues pl ON pl.player_id = p.id AND pl.league_id = prs.league_id
JOIN leagues l ON l.id = prs.league_id
JOIN grands_prix gp ON gp.id = prs.grand_prix_id
ORDER BY prs.league_id, gp.round_number, prs.total_points DESC;

COMMENT ON VIEW v_grand_prix_leaderboard IS 'Grand Prix results per league with rankings';

-- Player season detail view (league-specific with draft info)
CREATE OR REPLACE VIEW v_player_season_detail AS
SELECT
    pl.league_id,
    l.name AS league_name,
    l.season_id,
    p.id AS player_id,
    p.username,
    pl.team_name,  -- Changed from p.team_name
    gp.round_number,
    gp.event_name,
    gp.is_completed,
    prs.total_points,
    prs.breakdown_json,
    prs.calculated_at,
    d.driver1_code,
    d.driver2_code,
    d.driver3_code,
    d.wildcard_code,
    c.short_name AS constructor
FROM player_leagues pl
JOIN players p ON p.id = pl.player_id
JOIN leagues l ON l.id = pl.league_id
JOIN grands_prix gp ON gp.season_id = l.season_id
LEFT JOIN player_round_scores prs ON prs.player_id = p.id AND prs.league_id = pl.league_id AND prs.grand_prix_id = gp.id
LEFT JOIN LATERAL (
    SELECT
        dr1.code AS driver1_code,
        dr2.code AS driver2_code,
        dr3.code AS driver3_code,
        dr4.code AS wildcard_code,
        drafts.constructor_id
    FROM drafts
    JOIN drivers dr1 ON dr1.id = drafts.driver1_id
    JOIN drivers dr2 ON dr2.id = drafts.driver2_id
    JOIN drivers dr3 ON dr3.id = drafts.driver3_id
    JOIN drivers dr4 ON dr4.id = drafts.wildcard_id
    WHERE drafts.player_id = p.id AND drafts.league_id = pl.league_id AND drafts.grand_prix_id = gp.id
    LIMIT 1
) d ON TRUE
LEFT JOIN constructors c ON c.id = d.constructor_id
ORDER BY pl.league_id, p.id, gp.round_number;

COMMENT ON VIEW v_player_season_detail IS 'Detailed round-by-round performance per player per league';

-- Player performance statistics per league
CREATE OR REPLACE VIEW v_player_league_stats AS
SELECT
    p.id AS player_id,
    p.username,
    pl.team_name,  -- Changed from p.team_name
    pl.league_id,
    l.name AS league_name,
    l.season_id,
    COUNT(DISTINCT prs.grand_prix_id) AS rounds_participated,
    COUNT(DISTINCT gp.id) FILTER (WHERE gp.is_completed) AS total_completed_rounds,
    COALESCE(SUM(prs.total_points), 0) AS total_points,
    COALESCE(AVG(prs.total_points), 0) AS avg_points_per_round,
    COALESCE(MAX(prs.total_points), 0) AS best_round_score,
    COALESCE(MIN(prs.total_points), 0) AS worst_round_score,
    RANK() OVER (PARTITION BY pl.league_id ORDER BY COALESCE(SUM(prs.total_points), 0) DESC) AS current_rank
FROM players p
JOIN player_leagues pl ON pl.player_id = p.id
JOIN leagues l ON l.id = pl.league_id
LEFT JOIN grands_prix gp ON gp.season_id = l.season_id
LEFT JOIN player_round_scores prs ON prs.player_id = p.id AND prs.league_id = pl.league_id AND prs.grand_prix_id = gp.id
GROUP BY p.id, p.username, pl.team_name, pl.league_id, l.name, l.season_id;

COMMENT ON VIEW v_player_league_stats IS 'Statistical summary per player per league';

-- League summary view (player counts, activity)
CREATE OR REPLACE VIEW v_league_summary AS
SELECT
    l.id AS league_id,
    l.name AS league_name,
    l.discord_guild_id,
    l.season_id,
    s.year AS season_year,
    COUNT(DISTINCT pl.player_id) AS player_count,
    COUNT(DISTINCT prs.id) AS total_scores_submitted,
    COUNT(DISTINCT gp.id) FILTER (WHERE gp.is_completed) AS completed_rounds,
    COUNT(DISTINCT gp.id) AS total_rounds,
    l.created_at
FROM leagues l
JOIN seasons s ON s.id = l.season_id
LEFT JOIN player_leagues pl ON pl.league_id = l.id
LEFT JOIN grands_prix gp ON gp.season_id = l.season_id
LEFT JOIN player_round_scores prs ON prs.league_id = l.id AND prs.grand_prix_id = gp.id
GROUP BY l.id, l.name, l.discord_guild_id, l.season_id, s.year, l.created_at
ORDER BY l.created_at DESC;

COMMENT ON VIEW v_league_summary IS 'Overview of all leagues with participation stats';

-- Player cross-league view (see all leagues a player is in)
CREATE OR REPLACE VIEW v_player_leagues AS
SELECT
    p.id AS player_id,
    p.username,
    p.discord_user_id,
    pl.league_id,
    l.name AS league_name,
    l.season_id,
    s.year AS season_year,
    pl.joined_at,
    COUNT(DISTINCT prs.id) AS rounds_played_in_league,
    COALESCE(SUM(prs.total_points), 0) AS total_points_in_league
FROM players p
JOIN player_leagues pl ON pl.player_id = p.id
JOIN leagues l ON l.id = pl.league_id
JOIN seasons s ON s.id = l.season_id
LEFT JOIN player_round_scores prs ON prs.player_id = p.id AND prs.league_id = pl.league_id
LEFT JOIN grands_prix gp ON gp.id = prs.grand_prix_id AND gp.season_id = l.season_id
GROUP BY p.id, p.username, p.discord_user_id, pl.league_id, l.name, l.season_id, s.year, pl.joined_at
ORDER BY p.id, pl.joined_at DESC;

COMMENT ON VIEW v_player_leagues IS 'Shows all leagues each player participates in';

-- ============================================================
-- TRIGGER FUNCTIONS
-- ============================================================

-- Function to validate that at least one driver belongs to the selected constructor
CREATE OR REPLACE FUNCTION validate_draft_constructor_driver()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if at least one of the selected drivers belongs to the constructor
    IF NOT EXISTS (
        SELECT 1 FROM drivers d
        WHERE d.id = NEW.driver1_id AND d.constructor_id = NEW.constructor_id
    ) AND NOT EXISTS (
        SELECT 1 FROM drivers d
        WHERE d.id = NEW.driver2_id AND d.constructor_id = NEW.constructor_id
    ) AND NOT EXISTS (
        SELECT 1 FROM drivers d
        WHERE d.id = NEW.driver3_id AND d.constructor_id = NEW.constructor_id
    ) AND NOT EXISTS (
        SELECT 1 FROM drivers d
        WHERE d.id = NEW.wildcard_id AND d.constructor_id = NEW.constructor_id
    ) THEN
        RAISE EXCEPTION 'At least one driver must belong to the selected constructor (constructor_id: %)', NEW.constructor_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION validate_draft_constructor_driver IS 'Ensures at least one selected driver belongs to the chosen constructor';

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Trigger for INSERT operations on drafts
CREATE TRIGGER trg_drafts_validate_constructor_insert
    BEFORE INSERT ON drafts
    FOR EACH ROW
    EXECUTE FUNCTION validate_draft_constructor_driver();

-- Trigger for UPDATE operations on drafts
CREATE TRIGGER trg_drafts_validate_constructor_update
    BEFORE UPDATE ON drafts
    FOR EACH ROW
    WHEN (
        OLD.driver1_id IS DISTINCT FROM NEW.driver1_id OR
        OLD.driver2_id IS DISTINCT FROM NEW.driver2_id OR
        OLD.driver3_id IS DISTINCT FROM NEW.driver3_id OR
        OLD.wildcard_id IS DISTINCT FROM NEW.wildcard_id OR
        OLD.constructor_id IS DISTINCT FROM NEW.constructor_id
    )
    EXECUTE FUNCTION validate_draft_constructor_driver();

COMMENT ON TRIGGER trg_drafts_validate_constructor_insert ON drafts IS 'Validates constructor-driver relationship on insert';
COMMENT ON TRIGGER trg_drafts_validate_constructor_update ON drafts IS 'Validates constructor-driver relationship on update (only when relevant fields change)';