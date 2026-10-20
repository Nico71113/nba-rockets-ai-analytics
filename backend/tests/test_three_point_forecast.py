from datetime import date, timedelta

from backend.app.experiments.three_point_forecast import (
    ShootingObservation,
    build_three_point_forecast,
)


def _observations(second_half_delta: int = 0) -> tuple[list[date], list[ShootingObservation]]:
    dates = [date(2026, 1, 1) + timedelta(days=index) for index in range(8)]
    players = (
        (1, "Stable Shooter", (4, 10), (4, 10), (4 + second_half_delta, 10)),
        (2, "Hot Start", (8, 10), (6, 10), (2, 10)),
        (3, "Cold Start", (2, 10), (4, 10), (7, 10)),
    )
    rows = []
    for player_id, player_name, early, validation, test in players:
        period_lines = (early, early, validation, validation, test, test, test, test)
        for game_date, (made, attempted) in zip(dates, period_lines, strict=True):
            rows.append(
                ShootingObservation(
                    game_date=game_date,
                    player_id=player_id,
                    player_name=player_name,
                    team_name="Test Team",
                    made=made,
                    attempted=attempted,
                )
            )
    return dates, rows


def test_forecast_uses_nested_time_split_and_reports_all_baselines():
    dates, rows = _observations()

    result = build_three_point_forecast(
        season_id="test",
        game_dates=dates,
        observations=rows,
        minimum_attempts_per_half=1,
        validation_minimum_attempts=1,
        prior_strengths=(0, 2, 10),
        featured_player_name="Stable Shooter",
    )

    assert result.split.training_end == date(2026, 1, 4)
    assert result.split.testing_start == date(2026, 1, 5)
    assert result.cohort.players == 3
    assert {method.key for method in result.methods} == {
        "historical_rate",
        "league_mean",
        "shrinkage",
    }
    assert result.featured_player is not None
    assert result.featured_player.player_name == "Stable Shooter"


def test_future_results_cannot_change_fitted_predictions():
    dates, rows = _observations()
    _, changed_rows = _observations(second_half_delta=1)

    original = build_three_point_forecast(
        season_id="test",
        game_dates=dates,
        observations=rows,
        minimum_attempts_per_half=1,
        validation_minimum_attempts=1,
        prior_strengths=(0, 2, 10),
        featured_player_name="Stable Shooter",
    )
    changed = build_three_point_forecast(
        season_id="test",
        game_dates=dates,
        observations=changed_rows,
        minimum_attempts_per_half=1,
        validation_minimum_attempts=1,
        prior_strengths=(0, 2, 10),
        featured_player_name="Stable Shooter",
    )

    assert original.selected_prior_strength == changed.selected_prior_strength
    assert original.league_first_half_percentage == changed.league_first_half_percentage
    assert original.featured_player is not None
    assert changed.featured_player is not None
    assert (
        original.featured_player.shrinkage_prediction
        == changed.featured_player.shrinkage_prediction
    )
    assert (
        original.featured_player.second_half_percentage
        != changed.featured_player.second_half_percentage
    )
