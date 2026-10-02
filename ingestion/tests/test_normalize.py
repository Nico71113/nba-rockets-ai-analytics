import pytest

from ingestion.normalize import (
    _as_bool,
    _choose_minutes_encoding,
    _matches_game_teams,
    _minutes_to_seconds,
    _within_season,
)


def test_season_window_is_start_inclusive_and_end_exclusive():
    assert _within_season("2025-10-01 00:00:00")
    assert _within_season("2026-06-30 23:59:59")
    assert not _within_season("2025-09-30 23:59:59")
    assert not _within_season("2026-07-01 00:00:00")
    assert not _within_season("")


def test_boolean_parser_accepts_source_encodings():
    assert _as_bool("1")
    assert _as_bool("TRUE")
    assert not _as_bool("0")
    assert not _as_bool("false")
    with pytest.raises(ValueError, match="Invalid boolean"):
        _as_bool("")


def test_team_pair_must_match_both_teams_in_game():
    game = {"home_team_id": "HOU", "away_team_id": "OKC"}

    assert _matches_game_teams(game, "HOU", "OKC")
    assert _matches_game_teams(game, "OKC", "HOU")
    assert not _matches_game_teams(game, "0", "0")
    assert not _matches_game_teams(game, "HOU", "DAL")


def test_clock_minutes_are_reconciled_and_converted_to_seconds():
    values = ["47.03", "36.30", "0.06"]

    assert _choose_minutes_encoding(values, 5_019) == "clock"
    assert _minutes_to_seconds("47.03", "clock") == 2_823
    assert _minutes_to_seconds("36.3", "clock") == 2_190


def test_decimal_minutes_are_reconciled_and_converted_to_seconds():
    values = ["39.166666666666664", "36.5"]

    assert _choose_minutes_encoding(values, 4_540) == "decimal"
    assert _minutes_to_seconds("39.166666666666664", "decimal") == 2_350


def test_minutes_encoding_rejects_unreconciled_totals():
    with pytest.raises(ValueError, match="do not reconcile"):
        _choose_minutes_encoding(["10.00", "10.00"], 14_400)
