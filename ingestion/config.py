"""Shared constants for the fixed 2025-26 source snapshot."""

from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MANIFEST_DIR = DATA_DIR / "manifests"

SOURCE_HANDLE = "eoinamoore/historical-nba-data-and-player-box-scores"
SOURCE_URL = f"https://www.kaggle.com/datasets/{SOURCE_HANDLE}"
SOURCE_METADATA_URL = f"https://www.kaggle.com/api/v1/datasets/view/{SOURCE_HANDLE}"
EXPECTED_SOURCE_LICENSE = "CC0: Public Domain"

REQUIRED_SOURCE_FILES = (
    "Games.csv",
    "TeamStatistics.csv",
    "PlayerStatistics.csv",
    "Players.csv",
    "TeamHistories.csv",
    "LeagueSchedule25_26.csv",
)
OPTIONAL_PLAY_BY_PLAY_FILE = "PlayByPlay.parquet"

SEASON_ID = "2025-26"
SEASON_START = date(2025, 10, 1)
SEASON_END_EXCLUSIVE = date(2026, 7, 1)
INCLUDED_GAME_TYPES = frozenset(
    {
        "Regular Season",
        "Emirates NBA Cup",
        "Play-in Tournament",
        "Playoffs",
    }
)

HOUSTON_ROCKETS_TEAM_ID = "1610612745"
KEVIN_DURANT_PLAYER_ID = "201142"
