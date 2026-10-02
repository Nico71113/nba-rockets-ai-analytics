from ingestion.validate import reconcile_team_rows


def _game():
    return {
        "game_id": "g1",
        "home_team_id": "HOU",
        "away_team_id": "OKC",
        "home_score": "110",
        "away_score": "105",
        "winner_team_id": "HOU",
    }


def test_reconcile_team_rows_accepts_two_matching_box_scores():
    rows = [
        {
            "game_id": "g1",
            "team_id": "HOU",
            "opponent_team_id": "OKC",
            "is_home": "true",
            "won": "true",
            "team_score": "110",
        },
        {
            "game_id": "g1",
            "team_id": "OKC",
            "opponent_team_id": "HOU",
            "is_home": "false",
            "won": "false",
            "team_score": "105",
        },
    ]

    assert reconcile_team_rows({"g1": _game()}, rows) == []


def test_reconcile_team_rows_rejects_placeholder_source_row():
    rows = [
        {
            "game_id": "g1",
            "team_id": "HOU",
            "opponent_team_id": "OKC",
            "is_home": "true",
            "won": "true",
            "team_score": "110",
        },
        {
            "game_id": "g1",
            "team_id": "OKC",
            "opponent_team_id": "HOU",
            "is_home": "false",
            "won": "false",
            "team_score": "105",
        },
        {"game_id": "g1", "team_id": "0", "team_score": "0"},
    ]

    errors = reconcile_team_rows({"g1": _game()}, rows)

    assert "Game g1 has 3 team rows instead of 2" in errors
    assert "Team 0 is not part of game g1" in errors
