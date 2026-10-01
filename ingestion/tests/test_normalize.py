from ingestion.normalize import _as_bool, _matches_game_teams, _within_season


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
    assert not _as_bool("")


def test_team_pair_must_match_both_teams_in_game():
    game = {"home_team_id": "HOU", "away_team_id": "OKC"}

    assert _matches_game_teams(game, "HOU", "OKC")
    assert _matches_game_teams(game, "OKC", "HOU")
    assert not _matches_game_teams(game, "0", "0")
    assert not _matches_game_teams(game, "HOU", "DAL")
