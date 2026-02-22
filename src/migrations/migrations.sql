-- ============================================================
-- LVS F1 Fantasy League — PostgreSQL Schema
-- Designed for multi-client access (Discord bot, PWA, APIs)
-- ============================================================

-- Enable UUID support
--CREATE EXTENSION IF NOT EXISTS "pgcrypto";

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

-- ------------------------------------------------------------
-- CONSTRUCTORS (teams)
-- One row per constructor per season (names/colors change)
-- ------------------------------------------------------------
CREATE TABLE constructors (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    season_id       INT NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    short_name      TEXT NOT NULL,                          -- e.g. 'mclaren'
    full_name       TEXT NOT NULL,                          -- e.g. 'McLaren Formula 1 Team'
    color_hex       CHAR(7) NOT NULL DEFAULT '#FFFFFF',     -- e.g. '#CC6600'
    ergast_id       TEXT,                                   -- for API lookups
    UNIQUE (season_id, short_name)                          -- can't have more than one team per season
);

-- ------------------------------------------------------------
-- DRIVERS
-- One row per driver per season (team changes mid-season handled)
-- ------------------------------------------------------------
CREATE TABLE drivers (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    season_id       INT NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    code            CHAR(3) NOT NULL,                       -- e.g. 'VER'
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    constructor_id  INT NOT NULL REFERENCES constructors(id) ON DELETE CASCADE,
    ergast_id       TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,          -- excluded drivers = false
    UNIQUE (season_id, code)
);

CREATE INDEX idx_drivers_season ON drivers (season_id);

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

-- ------------------------------------------------------------
-- LEAGUES  (support multiple leagues / guilds)
-- ------------------------------------------------------------
CREATE TABLE leagues (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name            TEXT NOT NULL,
    discord_guild_id BIGINT UNIQUE,                          -- NULL if used by non-Discord client
    season_id       INT NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    embed_color     INT NOT NULL DEFAULT 0xE8272A,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- PLAYERS (league members)
-- ------------------------------------------------------------
CREATE TABLE players (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    league_id       INT NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    discord_user_id BIGINT,                                  -- NULL if non-Discord
    username        TEXT NOT NULL,
    password        VARCHAR(255),                            -- bcrypt hash, NULL if not using PWA
    team_name       TEXT,
    team_motto      TEXT,
    timezone        TEXT NOT NULL DEFAULT 'UTC',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (league_id, discord_user_id),
    UNIQUE (league_id, username),
    UNIQUE (league_id, team_name)
);

CREATE INDEX idx_players_league ON players (league_id);

-- ------------------------------------------------------------
-- DRAFTS  (one per player per GP)
-- ------------------------------------------------------------
CREATE TABLE drafts (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    player_id       INT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    grand_prix_id   INT NOT NULL REFERENCES grands_prix(id) ON DELETE CASCADE,
    driver1_id      INT NOT NULL REFERENCES drivers(id),
    driver2_id      INT NOT NULL REFERENCES drivers(id),
    driver3_id      INT NOT NULL REFERENCES drivers(id),
    wildcard_id     INT NOT NULL REFERENCES drivers(id),     -- "bogey" driver
    constructor_id  INT NOT NULL REFERENCES constructors(id),
    is_auto_assigned BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (player_id, grand_prix_id),
    CHECK (driver1_id != driver2_id AND driver2_id != driver3_id AND driver3_id != wildcard_id)
    -- Perform app-level check for at least one driver selected from the chosen constructor.
);

-- Prevent a player from picking the same driver in two slots (app-level too)
-- Enforced via CHECK + triggers or application logic

-- ------------------------------------------------------------
-- COUNTERPICKS  (driver bans)
-- ------------------------------------------------------------
CREATE TABLE counterpicks (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    grand_prix_id   INT NOT NULL REFERENCES grands_prix(id) ON DELETE CASCADE,
    picking_player_id   INT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    target_player_id    INT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    target_driver_id    INT NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One counterpick per picking player per round
    UNIQUE (grand_prix_id, picking_player_id),
    -- Can't counterpick yourself
    CHECK (picking_player_id != target_player_id)
);

-- ------------------------------------------------------------
-- RACE RESULTS (official finishing order, stored per GP)
-- ------------------------------------------------------------
CREATE TABLE race_results (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    grand_prix_id   INT NOT NULL REFERENCES grands_prix(id) ON DELETE CASCADE,
    session_type    TEXT NOT NULL,    -- 'qualifying' | 'race' | 'sprint' | 'sprint_qualifying'
    driver_id       INT NOT NULL REFERENCES drivers(id),
    position        SMALLINT NOT NULL,
    UNIQUE (grand_prix_id, session_type, driver_id)
);

CREATE INDEX idx_race_results_gp ON race_results (grand_prix_id, session_type);

-- ------------------------------------------------------------
-- PLAYER ROUND SCORES (calculated fantasy points per GP)
-- ------------------------------------------------------------
CREATE TABLE player_round_scores (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    player_id       INT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    grand_prix_id   INT NOT NULL REFERENCES grands_prix(id) ON DELETE CASCADE,
    total_points    INT NOT NULL DEFAULT 0,
    breakdown_json  JSONB NOT NULL DEFAULT '{}',             -- detailed breakdown
    calculated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (player_id, grand_prix_id)
);

CREATE INDEX idx_player_scores_player ON player_round_scores (player_id);

-- ------------------------------------------------------------
-- SCORING RULES  (configurable per season, no more hardcoding)
-- ------------------------------------------------------------
CREATE TABLE scoring_rules (
    id              INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    season_id       INT NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    rule_key        TEXT NOT NULL,    -- e.g. 'race_points', 'quali_points', 'bogey_points'
    rule_value      JSONB NOT NULL,  -- e.g. [25,18,15,12,10,8,6,4,2,1]
    UNIQUE (season_id, rule_key)
);

-- Seed default scoring rules for a season
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
-- VIEWS  (convenient for PWAs / dashboards)
-- ------------------------------------------------------------

-- Leaderboard view
CREATE OR REPLACE VIEW v_leaderboard AS
SELECT
    p.id AS player_id,
    p.username,
    p.team_name,
    l.id AS league_id,
    l.name AS league_name,
    COALESCE(SUM(prs.total_points), 0) AS total_points,
    COUNT(prs.id) AS rounds_played
FROM players p
         JOIN leagues l ON l.id = p.league_id
         LEFT JOIN player_round_scores prs ON prs.player_id = p.id
GROUP BY p.id, p.username, p.team_name, l.id, l.name
ORDER BY total_points DESC;

-- Player season detail view
CREATE OR REPLACE VIEW v_player_season_detail AS
SELECT
    p.id AS player_id,
    p.username,
    gp.round_number,
    gp.event_name,
    prs.total_points,
    prs.breakdown_json,
    d.draft_driver1_code,
    d.draft_driver2_code,
    d.draft_driver3_code,
    d.draft_wildcard_code,
    c.short_name AS constructor
FROM players p
         JOIN player_round_scores prs ON prs.player_id = p.id
         JOIN grands_prix gp ON gp.id = prs.grand_prix_id
         LEFT JOIN LATERAL (
    SELECT
        dr1.code AS draft_driver1_code,
        dr2.code AS draft_driver2_code,
        dr3.code AS draft_driver3_code,
        dr4.code AS draft_wildcard_code,
        drafts.constructor_id
    FROM drafts
             JOIN drivers dr1 ON dr1.id = drafts.driver1_id
             JOIN drivers dr2 ON dr2.id = drafts.driver2_id
             JOIN drivers dr3 ON dr3.id = drafts.driver3_id
             JOIN drivers dr4 ON dr4.id = drafts.wildcard_id
    WHERE drafts.player_id = p.id AND drafts.grand_prix_id = gp.id
    LIMIT 1
    ) d ON TRUE
         LEFT JOIN constructors c ON c.id = d.constructor_id
ORDER BY gp.round_number;