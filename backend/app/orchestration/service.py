from __future__ import annotations

import re
from calendar import monthrange
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.analytics.service import (
    game_result,
    player_availability,
    player_period_summary,
    team_record,
    team_record_when_player_reaches,
)
from backend.app.models import Game, Player, Team
from backend.app.orchestration.router import IntentRouterError, OllamaIntentRouter, ParsedIntent
from backend.app.schemas import AnalyticsResult, QueryResponse

TEAM_ALIASES = {
    "hou": "houston rockets",
    "okc": "oklahoma city thunder",
    "gsw": "golden state warriors",
    "nyk": "new york knicks",
    "lal": "los angeles lakers",
    "lac": "la clippers",
    "sas": "san antonio spurs",
}
STAT_TERMS = {
    "points": ("point", "points", "pts", "scored"),
    "assists": ("assist", "assists", "ast"),
    "rebounds": ("rebound", "rebounds", "reb"),
    "steals": ("steal", "steals"),
    "blocks": ("block", "blocks"),
    "turnovers": ("turnover", "turnovers"),
    "three_pointers_made": ("three pointer", "three pointers", "3pm", "threes"),
}
MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

UNSUPPORTED_QUESTION_RULES = (
    (
        ("defender", "guarded", "guarding", "matchup"),
        "The loaded snapshot has box scores, schedules, and availability rows, but no "
        "player-tracking or defensive-assignment data needed to identify who guarded a player.",
    ),
    (
        ("off ball", "off-ball", "screen angle", "cutting lane", "game video", "film"),
        "The loaded snapshot has no synchronized video or player-tracking coordinates, so it "
        "cannot measure off-ball movement or its effect on the defense.",
    ),
    (
        ("predict", "prediction", "project", "projection", "will win"),
        "This project calculates historical results from a fixed snapshot; it does not contain "
        "a validated predictive model.",
    ),
    (
        ("live score", "right now", "tonight's game", "todays game", "today's game"),
        "This project uses a fixed 2025-26 snapshot and has no live-data feed.",
    ),
)


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _resolve_team(session: Session, value: str | None) -> tuple[Team | None, str | None]:
    if not value:
        return None, "A team name is required."
    query = TEAM_ALIASES.get(_normalized(value), _normalized(value))
    teams = list(session.scalars(select(Team).order_by(Team.name)))
    exact = [team for team in teams if _normalized(team.name) == query]
    if len(exact) == 1:
        return exact[0], None
    partial = []
    for team in teams:
        name = _normalized(team.name)
        nickname = name.split()[-1]
        if (
            query in name.split()
            or query == nickname
            or query in name
            or name in query
            or nickname in query.split()
        ):
            partial.append(team)
    if len(partial) == 1:
        return partial[0], None
    if not partial:
        return None, f"No loaded team matches {value!r}."
    names = ", ".join(team.name for team in partial[:5])
    return None, f"The team name {value!r} is ambiguous: {names}."


def _resolve_player(session: Session, value: str | None) -> tuple[Player | None, str | None]:
    if not value:
        return None, "A player name is required."
    query = _normalized(value)
    players = list(session.scalars(select(Player).order_by(Player.last_name, Player.first_name)))
    exact = [
        player
        for player in players
        if _normalized(f"{player.first_name} {player.last_name}") == query
    ]
    if len(exact) == 1:
        return exact[0], None
    partial = []
    for player in players:
        full_name = _normalized(f"{player.first_name} {player.last_name}")
        last_name = _normalized(player.last_name)
        if (
            query == last_name
            or query in full_name
            or full_name in query
            or last_name in query.split()
        ):
            partial.append(player)
    if len(partial) == 1:
        return partial[0], None
    if not partial:
        return None, f"No loaded player matches {value!r}."
    names = ", ".join(f"{p.first_name} {p.last_name}" for p in partial[:5])
    return None, f"The player name {value!r} is ambiguous: {names}."


def _date_value(value: str | None, label: str) -> tuple[date | None, str | None]:
    if value is None:
        return None, f"A {label} is required."
    try:
        return date.fromisoformat(value), None
    except ValueError:
        return None, f"The {label} must be an ISO date, not {value!r}."


def _coverage_dates(session: Session, game_type: str) -> tuple[date | None, date | None]:
    return session.execute(
        select(func.min(Game.game_date), func.max(Game.game_date)).where(
            Game.game_type == game_type
        )
    ).one()


def _stat_from_question(question: str) -> str | None:
    normalized = _normalized(question)
    for stat, terms in STAT_TERMS.items():
        if any(term in normalized for term in terms):
            return stat
    return None


def _month_range_from_question(question: str) -> tuple[date, date] | None:
    match = re.search(
        r"\b(" + "|".join(MONTHS) + r")\s+(20\d{2})\b",
        question.casefold(),
    )
    if match is None:
        return None
    month = MONTHS[match.group(1)]
    year = int(match.group(2))
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def _explicit_date_from_question(question: str) -> date | None:
    match = re.search(
        r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2})(?:st|nd|rd|th)?[,]?\s+(20\d{2})\b",
        question.casefold(),
    )
    if match is None:
        return None
    try:
        return date(int(match.group(3)), MONTHS[match.group(1)], int(match.group(2)))
    except ValueError:
        return None


def _teams_in_question(session: Session, question: str) -> list[Team]:
    normalized = _normalized(question)
    matches: list[tuple[int, Team]] = []
    for team in session.scalars(select(Team).order_by(Team.name)):
        name = _normalized(team.name)
        nickname = name.split()[-1]
        positions = [
            position
            for term in (name, nickname)
            if (position := normalized.find(term)) >= 0
        ]
        if positions:
            matches.append((min(positions), team))
    return [team for _, team in sorted(matches, key=lambda item: item[0])]


def _known_coverage_gap(question: str) -> str | None:
    normalized = question.casefold()
    for terms, reason in UNSUPPORTED_QUESTION_RULES:
        if any(term in normalized for term in terms):
            return reason
    return None


def _refusal(question: str, intent: str, parsed: ParsedIntent, reason: str) -> QueryResponse:
    return QueryResponse(
        question=question,
        intent=intent,
        interpretation=parsed.model_dump(exclude_none=True),
        result=AnalyticsResult(method="refusal", answer=reason, coverage_note=reason),
    )


def answer_question(
    session: Session,
    *,
    question: str,
    router: OllamaIntentRouter,
) -> QueryResponse:
    coverage_gap = _known_coverage_gap(question)
    if coverage_gap:
        parsed = ParsedIntent(intent="unsupported", reason=coverage_gap)
        return _refusal(question, parsed.intent, parsed, coverage_gap)

    try:
        parsed = router.parse(question)
    except IntentRouterError as error:
        fallback = ParsedIntent(intent="unsupported", reason=str(error))
        return _refusal(
            question,
            "router_unavailable",
            fallback,
            "The local language model is unavailable, so the question could not be interpreted. "
            f"Technical detail: {error}",
        )

    if parsed.intent == "unsupported":
        reason = parsed.reason or (
            "The question requires data outside box scores, schedules, "
            "and source availability rows."
        )
        return _refusal(question, parsed.intent, parsed, reason)

    player = team = opponent = None
    errors: list[str] = []
    mentioned_teams = _teams_in_question(session, question)
    team_value = parsed.team_name
    opponent_value = parsed.opponent_name
    if not team_value and mentioned_teams:
        team_value = mentioned_teams[0].name
    if parsed.intent in {"game_result", "player_availability"} and not opponent_value:
        primary_name = _normalized(team_value) if team_value else None
        opponent_value = next(
            (
                mentioned.name
                for mentioned in mentioned_teams
                if _normalized(mentioned.name) != primary_name
            ),
            None,
        )
    if parsed.intent in {"player_summary", "threshold_record", "player_availability"}:
        player, error = _resolve_player(session, parsed.player_name or question)
        if error:
            errors.append(error)
    if parsed.intent in {
        "team_record",
        "threshold_record",
        "game_result",
        "player_availability",
    } or team_value:
        team, error = _resolve_team(session, team_value)
        if error:
            errors.append(error)
    if parsed.intent in {"game_result", "player_availability"} or opponent_value:
        opponent, error = _resolve_team(session, opponent_value)
        if error:
            errors.append(error)
    if errors:
        return _refusal(question, parsed.intent, parsed, " ".join(errors))

    if parsed.intent in {"player_summary", "team_record", "threshold_record"}:
        coverage_start, coverage_end = _coverage_dates(session, parsed.game_type)
        explicit_month = _month_range_from_question(question)
        if explicit_month:
            start_date, end_date = explicit_month
            start_error = end_error = None
        else:
            start_date, start_error = (
                _date_value(parsed.start_date, "start date")
                if parsed.start_date
                else (coverage_start, None)
            )
            end_date, end_error = (
                _date_value(parsed.end_date, "end date")
                if parsed.end_date
                else (coverage_end, None)
            )
        if start_error or end_error or start_date is None or end_date is None:
            reason = start_error or end_error or f"No {parsed.game_type} coverage is loaded."
            return _refusal(question, parsed.intent, parsed, reason)
        if start_date > end_date:
            return _refusal(
                question, parsed.intent, parsed, "The start date must be on or before the end date."
            )

    if parsed.intent == "player_summary":
        result = player_period_summary(
            session,
            player_id=player.player_id,
            team_id=team.team_id if team else None,
            start_date=start_date,
            end_date=end_date,
            game_type=parsed.game_type,
        )
    elif parsed.intent == "team_record":
        result = team_record(
            session,
            team_id=team.team_id,
            start_date=start_date,
            end_date=end_date,
            game_type=parsed.game_type,
        )
    elif parsed.intent == "threshold_record":
        stat = parsed.stat or _stat_from_question(question)
        if stat is None or parsed.threshold is None:
            return _refusal(
                question,
                parsed.intent,
                parsed,
                "A supported box-score stat and numeric threshold are required.",
            )
        result = team_record_when_player_reaches(
            session,
            team_id=team.team_id,
            player_id=player.player_id,
            stat=stat,
            threshold=parsed.threshold,
            start_date=start_date,
            end_date=end_date,
            game_type=parsed.game_type,
        )
    elif parsed.intent == "game_result":
        explicit_date = _explicit_date_from_question(question)
        game_date, error = _date_value(
            explicit_date.isoformat() if explicit_date else parsed.game_date,
            "game date",
        )
        if error or game_date is None:
            return _refusal(question, parsed.intent, parsed, error or "A game date is required.")
        result = game_result(
            session,
            team_id=team.team_id,
            opponent_team_id=opponent.team_id,
            game_date=game_date,
        )
    else:
        explicit_date = _explicit_date_from_question(question)
        game_date, error = _date_value(
            explicit_date.isoformat() if explicit_date else parsed.game_date,
            "game date",
        )
        if error or game_date is None:
            return _refusal(question, parsed.intent, parsed, error or "A game date is required.")
        result = player_availability(
            session,
            player_id=player.player_id,
            team_id=team.team_id,
            opponent_team_id=opponent.team_id if opponent else None,
            game_date=game_date,
        )

    interpretation: dict[str, object] = {
        "intent": parsed.intent,
        "game_type": parsed.game_type,
    }
    if parsed.intent in {"player_summary", "team_record", "threshold_record"}:
        interpretation["start_date"] = start_date.isoformat()
        interpretation["end_date"] = end_date.isoformat()
    if player:
        interpretation["player_name"] = f"{player.first_name} {player.last_name}"
        interpretation["player_id"] = player.player_id
    if team:
        interpretation["team_name"] = team.name
        interpretation["team_id"] = team.team_id
    if opponent:
        interpretation["opponent_name"] = opponent.name
        interpretation["opponent_team_id"] = opponent.team_id
    if parsed.intent == "threshold_record":
        interpretation["stat"] = stat
        interpretation["threshold"] = parsed.threshold
    if parsed.intent in {"game_result", "player_availability"}:
        interpretation["game_date"] = game_date.isoformat()
    return QueryResponse(
        question=question,
        intent=parsed.intent,
        interpretation=interpretation,
        result=result,
    )
