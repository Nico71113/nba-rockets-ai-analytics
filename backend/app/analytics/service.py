from __future__ import annotations

from datetime import date

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from backend.app.models import Game, Player, PlayerGameStat, Team, TeamGameStat
from backend.app.schemas import AnalyticsResult, Evidence

SUPPORTED_PLAYER_STATS = {
    "points": PlayerGameStat.points,
    "assists": PlayerGameStat.assists,
    "rebounds": PlayerGameStat.total_rebounds,
    "steals": PlayerGameStat.steals,
    "blocks": PlayerGameStat.blocks,
    "turnovers": PlayerGameStat.turnovers,
    "three_pointers_made": PlayerGameStat.three_pointers_made,
}

SUPPORTED_TEAM_STATS = {
    "points": TeamGameStat.team_score,
    "opponent_points": TeamGameStat.opponent_score,
    "assists": TeamGameStat.assists,
    "rebounds": TeamGameStat.total_rebounds,
    "offensive_rebounds": TeamGameStat.offensive_rebounds,
    "defensive_rebounds": TeamGameStat.defensive_rebounds,
    "steals": TeamGameStat.steals,
    "blocks": TeamGameStat.blocks,
    "turnovers": TeamGameStat.turnovers,
    "three_pointers_made": TeamGameStat.three_pointers_made,
    "point_margin": TeamGameStat.plus_minus,
}

SUPPORTED_AGGREGATIONS = {"sum", "average", "maximum", "minimum"}
SUPPORTED_LOCATIONS = {"all", "home", "away"}
SUPPORTED_OUTCOMES = {"all", "win", "loss"}


def _round(value: float | None, digits: int = 1) -> float | None:
    return round(float(value), digits) if value is not None else None


def _player_name(session: Session, player_id: int) -> str:
    player = session.get(Player, player_id)
    return f"{player.first_name} {player.last_name}" if player else f"Player {player_id}"


def _team_name(session: Session, team_id: int) -> str:
    team = session.get(Team, team_id)
    return team.name if team else f"Team {team_id}"


def metric_summary(
    session: Session,
    *,
    entity_type: str,
    entity_id: int,
    team_id: int | None = None,
    stat: str,
    aggregation: str,
    start_date: date,
    end_date: date,
    game_type: str = "Regular Season",
    location: str = "all",
    outcome: str = "all",
) -> AnalyticsResult:
    if aggregation not in SUPPORTED_AGGREGATIONS:
        return AnalyticsResult(
            method="refusal",
            answer=f"The aggregation {aggregation!r} is not supported.",
            coverage_note="Supported aggregations: sum, average, maximum, minimum.",
        )
    if location not in SUPPORTED_LOCATIONS or outcome not in SUPPORTED_OUTCOMES:
        return AnalyticsResult(
            method="refusal",
            answer="The requested split is not supported.",
            coverage_note="Location can be all/home/away and outcome can be all/win/loss.",
        )

    if entity_type == "player":
        entity = session.get(Player, entity_id)
        model = PlayerGameStat
        registry = SUPPORTED_PLAYER_STATS
        entity_name = (
            f"{entity.first_name} {entity.last_name}" if entity else f"Player {entity_id}"
        )
        conditions = [
            PlayerGameStat.player_id == entity_id,
            PlayerGameStat.did_play.is_(True),
        ]
        if team_id is not None:
            if session.get(Team, team_id) is None:
                return AnalyticsResult(
                    method="refusal",
                    answer=f"Team {team_id} is not present in the loaded snapshot.",
                    coverage_note="Choose a team returned by this snapshot.",
                )
            conditions.append(PlayerGameStat.team_id == team_id)
    elif entity_type == "team":
        entity = session.get(Team, entity_id)
        model = TeamGameStat
        registry = SUPPORTED_TEAM_STATS
        entity_name = entity.name if entity else f"Team {entity_id}"
        conditions = [TeamGameStat.team_id == entity_id]
    else:
        return AnalyticsResult(
            method="refusal",
            answer=f"The entity type {entity_type!r} is not supported.",
            coverage_note="Choose either a player or a team.",
        )

    if entity is None:
        return AnalyticsResult(
            method="refusal",
            answer=f"{entity_name} is not present in the loaded snapshot.",
            coverage_note="Choose an entity returned by this snapshot.",
        )
    column = registry.get(stat)
    if column is None:
        supported = ", ".join(sorted(registry))
        return AnalyticsResult(
            method="refusal",
            answer=f"The {entity_type} stat {stat!r} is not supported.",
            coverage_note=f"Supported {entity_type} stats: {supported}.",
        )

    conditions.extend(
        [
            Game.game_date >= start_date,
            Game.game_date <= end_date,
            Game.game_type == game_type,
        ]
    )
    if location != "all":
        conditions.append(model.is_home.is_(location == "home"))
    if outcome != "all":
        conditions.append(model.won.is_(outcome == "win"))

    aggregate_expression = {
        "sum": func.sum(column),
        "average": func.avg(column),
        "maximum": func.max(column),
        "minimum": func.min(column),
    }[aggregation]
    games, raw_value = session.execute(
        select(func.count(model.game_id), aggregate_expression)
        .join(Game, Game.game_id == model.game_id)
        .where(*conditions)
    ).one()
    games = int(games or 0)
    if games == 0 or raw_value is None:
        return AnalyticsResult(
            method="refusal",
            answer=f"No qualifying games were found for {entity_name}.",
            coverage_note=(
                "The entity exists, but no rows match the requested dates, game type, "
                "location, and outcome filters."
            ),
        )

    value: int | float
    if aggregation in {"sum", "maximum", "minimum"}:
        value = int(raw_value)
    else:
        value = _round(raw_value) or 0.0
    game_ids = list(
        session.scalars(
            select(model.game_id)
            .join(Game, Game.game_id == model.game_id)
            .where(*conditions)
            .order_by(Game.game_date, model.game_id)
        )
    )
    split_parts = []
    if location == "home":
        split_parts.append("at home")
    elif location == "away":
        split_parts.append("on the road")
    if outcome == "win":
        split_parts.append("in wins")
    elif outcome == "loss":
        split_parts.append("in losses")
    split = f" {' '.join(split_parts)}" if split_parts else ""
    stat_label = stat.replace("_", " ")
    verb = {
        "sum": f"recorded {value} total {stat_label}",
        "average": f"averaged {value} {stat_label} per game",
        "maximum": f"had a single-game high of {value} {stat_label}",
        "minimum": f"had a single-game low of {value} {stat_label}",
    }[aggregation]
    return AnalyticsResult(
        method="sql",
        answer=(
            f"{entity_name} {verb}{split} across {games} qualifying games "
            f"from {start_date} through {end_date}."
        ),
        metrics={
            "games": games,
            "value": value,
            "stat": stat,
            "aggregation": aggregation,
            "location": location,
            "outcome": outcome,
        },
        calculation=[
            f"Filter {entity_type}-game rows by date, game type, location, and outcome.",
            f"Apply the registered {aggregation} operation to the {stat_label} field.",
        ],
        evidence=[
            Evidence(
                source_table=f"{entity_type}_game_stats + games",
                game_ids=game_ids,
                filters={
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "team_id": team_id,
                    "stat": stat,
                    "aggregation": aggregation,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "game_type": game_type,
                    "location": location,
                    "outcome": outcome,
                },
            )
        ],
    )


def player_period_summary(
    session: Session,
    *,
    player_id: int,
    start_date: date,
    end_date: date,
    team_id: int | None = None,
    game_type: str = "Regular Season",
) -> AnalyticsResult:
    player = session.get(Player, player_id)
    if player is None:
        return AnalyticsResult(
            method="refusal",
            answer=f"Player {player_id} is not present in the loaded snapshot.",
            coverage_note="Choose a player returned by this snapshot's player search.",
        )
    if team_id is not None and session.get(Team, team_id) is None:
        return AnalyticsResult(
            method="refusal",
            answer=f"Team {team_id} is not present in the loaded snapshot.",
            coverage_note="Choose a team returned by this snapshot's team search.",
        )
    conditions = [
        PlayerGameStat.player_id == player_id,
        PlayerGameStat.did_play.is_(True),
        Game.game_date >= start_date,
        Game.game_date <= end_date,
        Game.game_type == game_type,
    ]
    if team_id is not None:
        conditions.append(PlayerGameStat.team_id == team_id)

    metrics = session.execute(
        select(
            func.count(PlayerGameStat.game_id),
            func.sum(PlayerGameStat.points),
            func.avg(PlayerGameStat.points),
            func.avg(PlayerGameStat.total_rebounds),
            func.avg(PlayerGameStat.assists),
        )
        .join(Game, Game.game_id == PlayerGameStat.game_id)
        .where(*conditions)
    ).one()
    games_played = int(metrics[0] or 0)
    player_name = f"{player.first_name} {player.last_name}"
    if games_played == 0:
        available_rows = session.scalar(
            select(func.count(PlayerGameStat.game_id))
            .join(Game, Game.game_id == PlayerGameStat.game_id)
            .where(
                PlayerGameStat.player_id == player_id,
                Game.game_date >= start_date,
                Game.game_date <= end_date,
                Game.game_type == game_type,
                *([PlayerGameStat.team_id == team_id] if team_id is not None else []),
            )
        ) or 0
        if available_rows:
            reason = (
                f"{available_rows} player availability row(s) exist, but none are marked as played."
            )
        else:
            coverage = session.execute(
                select(func.min(Game.game_date), func.max(Game.game_date), func.count(Game.game_id))
                .where(Game.game_type == game_type)
            ).one()
            if not coverage[2]:
                reason = f"The game type {game_type!r} is outside the loaded snapshot."
            elif end_date < coverage[0] or start_date > coverage[1]:
                reason = (
                    f"The requested dates are outside the loaded snapshot "
                    f"({coverage[0]} through {coverage[1]} for {game_type})."
                )
            else:
                reason = "No player-game row exists for the requested filters."
        return AnalyticsResult(
            method="refusal",
            answer=f"No played games were found for {player_name} in that date range.",
            coverage_note=reason,
            evidence=[
                Evidence(
                    source_table="player_game_stats + games",
                    filters={
                        "player_id": player_id,
                        "team_id": team_id,
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "game_type": game_type,
                        "did_play": True,
                    },
                )
            ],
        )

    game_ids = list(
        session.scalars(
            select(PlayerGameStat.game_id)
            .join(Game, Game.game_id == PlayerGameStat.game_id)
            .where(*conditions)
            .order_by(Game.game_date)
        )
    )
    total_points = int(metrics[1] or 0)
    averages = {
        "points_per_game": _round(metrics[2]),
        "rebounds_per_game": _round(metrics[3]),
        "assists_per_game": _round(metrics[4]),
    }
    answer = (
        f"{player_name} played {games_played} games and scored {total_points} total points "
        f"({averages['points_per_game']} per game) from {start_date} through {end_date}."
    )
    return AnalyticsResult(
        method="sql",
        answer=answer,
        metrics={"games_played": games_played, "total_points": total_points, **averages},
        calculation=[
            "Filter player-game rows by player, team, date range, game type, and did_play=true.",
            f"Sum points across {games_played} qualifying rows.",
            "Compute per-game averages over the same qualifying rows.",
        ],
        evidence=[
            Evidence(
                source_table="player_game_stats + games",
                game_ids=game_ids,
                filters={
                    "player_id": player_id,
                    "team_id": team_id,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "game_type": game_type,
                },
            )
        ],
    )


def team_record(
    session: Session,
    *,
    team_id: int,
    start_date: date,
    end_date: date,
    game_type: str = "Regular Season",
    location: str = "all",
) -> AnalyticsResult:
    if session.get(Team, team_id) is None:
        return AnalyticsResult(
            method="refusal",
            answer=f"Team {team_id} is not present in the loaded snapshot.",
            coverage_note="Choose a team returned by this snapshot's team search.",
        )
    conditions = [
        TeamGameStat.team_id == team_id,
        Game.game_date >= start_date,
        Game.game_date <= end_date,
        Game.game_type == game_type,
    ]
    if location not in SUPPORTED_LOCATIONS:
        return AnalyticsResult(
            method="refusal",
            answer=f"The location split {location!r} is not supported.",
            coverage_note="Location can be all, home, or away.",
        )
    if location != "all":
        conditions.append(TeamGameStat.is_home.is_(location == "home"))
    games, wins = session.execute(
        select(
            func.count(TeamGameStat.game_id),
            func.sum(case((TeamGameStat.won.is_(True), 1), else_=0)),
        )
        .join(Game, Game.game_id == TeamGameStat.game_id)
        .where(*conditions)
    ).one()
    games = int(games or 0)
    wins = int(wins or 0)
    losses = games - wins
    name = _team_name(session, team_id)
    game_ids = list(
        session.scalars(
            select(TeamGameStat.game_id)
            .join(Game, Game.game_id == TeamGameStat.game_id)
            .where(*conditions)
            .order_by(Game.game_date)
        )
    )
    if games == 0:
        return AnalyticsResult(
            method="refusal",
            answer=f"No {game_type.lower()} games were found for {name} in that date range.",
            coverage_note="The team, dates, or game type are outside the loaded snapshot.",
        )
    return AnalyticsResult(
        method="sql",
        answer=(
            f"{name} went {wins}-{losses}"
            f"{' at home' if location == 'home' else ' on the road' if location == 'away' else ''} "
            f"from {start_date} through {end_date}."
        ),
        metrics={"games": games, "wins": wins, "losses": losses},
        calculation=["Count qualifying team-game rows and sum the rows marked won=true."],
        evidence=[
            Evidence(
                source_table="team_game_stats + games",
                game_ids=game_ids,
                filters={
                    "team_id": team_id,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "game_type": game_type,
                    "location": location,
                },
            )
        ],
    )


def team_record_when_player_reaches(
    session: Session,
    *,
    team_id: int,
    player_id: int,
    stat: str,
    threshold: int,
    start_date: date,
    end_date: date,
    game_type: str = "Regular Season",
) -> AnalyticsResult:
    if session.get(Team, team_id) is None:
        return AnalyticsResult(
            method="refusal",
            answer=f"Team {team_id} is not present in the loaded snapshot.",
            coverage_note="Choose a team returned by this snapshot's team search.",
        )
    if session.get(Player, player_id) is None:
        return AnalyticsResult(
            method="refusal",
            answer=f"Player {player_id} is not present in the loaded snapshot.",
            coverage_note="Choose a player returned by this snapshot's player search.",
        )
    column = SUPPORTED_PLAYER_STATS.get(stat)
    if column is None:
        supported = ", ".join(sorted(SUPPORTED_PLAYER_STATS))
        return AnalyticsResult(
            method="refusal",
            answer=f"The stat '{stat}' is not supported.",
            coverage_note=f"Supported player stats: {supported}.",
        )

    conditions = [
        PlayerGameStat.player_id == player_id,
        PlayerGameStat.team_id == team_id,
        PlayerGameStat.did_play.is_(True),
        column >= threshold,
        Game.game_date >= start_date,
        Game.game_date <= end_date,
        Game.game_type == game_type,
    ]
    rows = session.execute(
        select(Game.game_id, TeamGameStat.won)
        .join(PlayerGameStat, PlayerGameStat.game_id == Game.game_id)
        .join(
            TeamGameStat,
            and_(
                TeamGameStat.game_id == Game.game_id,
                TeamGameStat.team_id == PlayerGameStat.team_id,
            ),
        )
        .where(*conditions)
        .order_by(Game.game_date)
    ).all()
    if not rows:
        return AnalyticsResult(
            method="sql",
            answer=f"No games matched the condition {stat} >= {threshold}.",
            metrics={"games": 0, "wins": 0, "losses": 0, "threshold": threshold},
            calculation=[
                f"Filter played player-game rows where {stat} >= {threshold}.",
                "The complete filtered result contains zero rows.",
            ],
            evidence=[
                Evidence(
                    source_table="player_game_stats + team_game_stats + games",
                    filters={
                        "team_id": team_id,
                        "player_id": player_id,
                        "stat": stat,
                        "threshold": threshold,
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "game_type": game_type,
                    },
                )
            ],
        )

    wins = sum(bool(row.won) for row in rows)
    games = len(rows)
    losses = games - wins
    player_name = _player_name(session, player_id)
    team_name = _team_name(session, team_id)
    return AnalyticsResult(
        method="sql",
        answer=(
            f"{team_name} went {wins}-{losses} when {player_name} recorded "
            f"at least {threshold} {stat.replace('_', ' ')}."
        ),
        metrics={"games": games, "wins": wins, "losses": losses, "threshold": threshold},
        calculation=[
            f"Filter played player-game rows where {stat} >= {threshold}.",
            "Join the matching game IDs to the team's win/loss rows.",
        ],
        evidence=[
            Evidence(
                source_table="player_game_stats + team_game_stats + games",
                game_ids=[row.game_id for row in rows],
                filters={
                    "team_id": team_id,
                    "player_id": player_id,
                    "stat": stat,
                    "threshold": threshold,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "game_type": game_type,
                },
            )
        ],
    )


def player_availability(
    session: Session,
    *,
    player_id: int,
    team_id: int,
    game_date: date,
    opponent_team_id: int | None = None,
) -> AnalyticsResult:
    player = session.get(Player, player_id)
    team = session.get(Team, team_id)
    if player is None or team is None:
        missing = f"player {player_id}" if player is None else f"team {team_id}"
        return AnalyticsResult(
            method="refusal",
            answer=f"The requested {missing} is not present in the loaded snapshot.",
            coverage_note="The system cannot infer availability for an unresolved entity.",
        )

    game_conditions = [
        Game.game_date == game_date,
        or_(Game.home_team_id == team_id, Game.away_team_id == team_id),
    ]
    if opponent_team_id is not None:
        game_conditions.append(
            or_(Game.home_team_id == opponent_team_id, Game.away_team_id == opponent_team_id)
        )
    games = list(session.scalars(select(Game).where(*game_conditions).order_by(Game.game_id)))
    player_name = f"{player.first_name} {player.last_name}"
    if not games:
        return AnalyticsResult(
            method="refusal",
            answer=f"No {team.name} game was found on {game_date}.",
            coverage_note="Without a matching game, no availability row can be checked.",
        )
    if len(games) > 1:
        return AnalyticsResult(
            method="refusal",
            answer=f"More than one {team.name} game was found on {game_date}.",
            coverage_note="Specify the opponent so the game can be identified uniquely.",
        )

    game = games[0]
    evidence = Evidence(
        source_table="games + player_game_stats",
        game_ids=[game.game_id],
        filters={
            "player_id": player_id,
            "team_id": team_id,
            "opponent_team_id": opponent_team_id,
            "game_date": game_date.isoformat(),
        },
    )
    row = session.scalar(
        select(PlayerGameStat).where(
            PlayerGameStat.game_id == game.game_id,
            PlayerGameStat.player_id == player_id,
            PlayerGameStat.team_id == team_id,
        )
    )
    if row is None:
        return AnalyticsResult(
            method="refusal",
            answer=f"{team.name} played, but no availability row exists for {player_name}.",
            coverage_note=(
                "The source omits this player from the game's player rows, so the reason for "
                "the absence cannot be determined without another source."
            ),
            evidence=[evidence],
        )
    if row.did_play:
        minutes = round((row.minutes_seconds or 0) / 60, 1)
        return AnalyticsResult(
            method="sql",
            answer=f"{player_name} played {minutes} minutes in that game.",
            metrics={"did_play": 1, "minutes": minutes},
            calculation=["Read the matched player-game availability and playing-time row."],
            evidence=[evidence],
        )
    if row.availability_comment:
        return AnalyticsResult(
            method="sql",
            answer=f"{player_name} did not play. Source status: {row.availability_comment}.",
            metrics={"did_play": 0},
            calculation=["Read the source-provided availability comment; no reason was inferred."],
            evidence=[evidence],
        )
    return AnalyticsResult(
        method="refusal",
        answer=f"{player_name} is marked as not playing, but no reason is provided.",
        coverage_note="The system will not invent an injury or coaching reason.",
        evidence=[evidence],
    )


def game_result(
    session: Session,
    *,
    team_id: int,
    opponent_team_id: int,
    game_date: date,
) -> AnalyticsResult:
    game = session.scalar(
        select(Game).where(
            Game.game_date == game_date,
            or_(
                and_(Game.home_team_id == team_id, Game.away_team_id == opponent_team_id),
                and_(Game.home_team_id == opponent_team_id, Game.away_team_id == team_id),
            ),
        )
    )
    if game is None:
        return AnalyticsResult(
            method="refusal",
            answer="No game between those teams was found on that date.",
            coverage_note="Check the team IDs, date, and loaded season coverage.",
        )

    home_name = _team_name(session, game.home_team_id)
    away_name = _team_name(session, game.away_team_id)
    winner_name = _team_name(session, game.winner_team_id)
    return AnalyticsResult(
        method="sql",
        answer=(
            f"{winner_name} won. Final score: {away_name} {game.away_score}, "
            f"{home_name} {game.home_score}."
        ),
        metrics={
            "home_score": game.home_score,
            "away_score": game.away_score,
            "winner_team_id": game.winner_team_id,
        },
        evidence=[
            Evidence(
                source_table="games",
                game_ids=[game.game_id],
                filters={
                    "team_id": team_id,
                    "opponent_team_id": opponent_team_id,
                    "game_date": game_date.isoformat(),
                },
            )
        ],
    )
