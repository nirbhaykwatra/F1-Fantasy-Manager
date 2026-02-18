import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

@dataclass(frozen=True)
class Config:
    # Discord
    token: str
    guild_id: int
    mode: str  # 'PROD' | 'DEV'

    # Postgres — single database
    database_url: str

    # Paths
    base_dir: Path
    cmds_dir: Path
    fastf1_cache_dir: Path

    # F1
    season: int
    current_round: int

    # Appearance
    embed_color: tuple[int, int, int] = (232, 39, 42)


def load_config() -> Config:
    load_dotenv()
    base_dir = Path(__file__).resolve().parent.parent
    cmds_dir = Path(__file__).resolve().parent / "commands"
    mode = os.getenv("MODE", "DEV")

    token = os.getenv("TOKEN") if mode == "PROD" else os.getenv("DEV_TOKEN")
    guild_id_key = "GUILD_ID" if mode == "PROD" else "DEV_GUILD_ID"

    db_user = os.getenv("SQLUSER")
    db_pass = os.getenv("SQLPASS")
    db_host = os.getenv("SQLHOST", "localhost")
    db_name = os.getenv("SQLDB", "lvs_f1_fantasy")
    database_url = f"postgresql+asyncpg://{db_user}:{db_pass}@{db_host}/{db_name}"

    return Config(
        token=token,
        guild_id=int(os.getenv(guild_id_key)),
        mode=mode,
        database_url=database_url,
        base_dir=base_dir,
        cmds_dir=cmds_dir,
        fastf1_cache_dir=base_dir / "data" / "fastf1" / "cache",
        season=int(os.getenv("F1_SEASON", "2025")),
        current_round=int(os.getenv("F1_ROUND", "1")),
    )