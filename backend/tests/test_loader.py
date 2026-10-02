import pytest

from ingestion.load_postgres import _bool, _datetime, _player_game_row


def test_datetime_parser_preserves_source_offset():
    parsed = _datetime("2026-01-05T20:00:00-05:00")

    assert parsed is not None
    assert parsed.utcoffset().total_seconds() == -5 * 60 * 60


def test_datetime_parser_rejects_naive_values():
    with pytest.raises(ValueError, match="UTC offset"):
        _datetime("2026-01-05T20:00:00")


def test_boolean_parser_rejects_missing_or_corrupt_values():
    assert _bool("true") is True
    assert _bool("0") is False
    with pytest.raises(ValueError, match="Invalid boolean"):
        _bool("")


def test_dnp_box_score_values_become_null():
    row = {
        "game_id": "g1",
        "player_id": "201142",
        "team_id": "1610612745",
        "opponent_team_id": "1610612760",
        "is_home": "true",
        "won": "false",
        "did_play": "false",
        "minutes_seconds": "",
        "points": "0",
        "assists": "0",
        "blocks": "0",
        "steals": "0",
        "field_goals_attempted": "0",
        "field_goals_made": "0",
        "field_goal_percentage": "0.0",
        "three_pointers_attempted": "0",
        "three_pointers_made": "0",
        "three_point_percentage": "0.0",
        "free_throws_attempted": "0",
        "free_throws_made": "0",
        "free_throw_percentage": "0.0",
        "defensive_rebounds": "0",
        "offensive_rebounds": "0",
        "total_rebounds": "0",
        "personal_fouls": "0",
        "turnovers": "0",
        "plus_minus": "0",
        "availability_comment": "DND - Injury/Illness",
        "starting_position": "",
    }

    converted = _player_game_row(row)

    assert converted["did_play"] is False
    assert converted["points"] is None
    assert converted["minutes_seconds"] is None
    assert converted["field_goal_percentage"] is None
    assert converted["availability_comment"] == "DND - Injury/Illness"
