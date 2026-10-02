from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "teams"

    team_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)


class Player(Base):
    __tablename__ = "players"

    player_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date)
    school: Mapped[str | None] = mapped_column(String(160))
    country: Mapped[str | None] = mapped_column(String(100))
    height_inches: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    weight_lbs: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    position_guard: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position_forward: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position_center: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    from_year: Mapped[int | None] = mapped_column(Integer)
    to_year: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (Index("ix_players_name", "last_name", "first_name"),)


class Game(Base):
    __tablename__ = "games"

    game_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    season_id: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    tipoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    game_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    game_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), nullable=False)
    home_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    away_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    winner_team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), nullable=False)
    attendance: Mapped[int | None] = mapped_column(Integer)
    arena_name: Mapped[str | None] = mapped_column(String(160))

    __table_args__ = (
        CheckConstraint("home_team_id <> away_team_id", name="ck_games_distinct_teams"),
        CheckConstraint("home_score >= 0 AND away_score >= 0", name="ck_games_nonnegative_score"),
        CheckConstraint("home_score <> away_score", name="ck_games_no_ties"),
        CheckConstraint(
            "winner_team_id IN (home_team_id, away_team_id)",
            name="ck_games_winner_participated",
        ),
        CheckConstraint(
            "(home_score > away_score AND winner_team_id = home_team_id) OR "
            "(away_score > home_score AND winner_team_id = away_team_id)",
            name="ck_games_winner_matches_score",
        ),
        Index("ix_games_season_type_date", "season_id", "game_type", "game_date", "game_id"),
        Index("ix_games_home_team_date", "home_team_id", "game_date"),
        Index("ix_games_away_team_date", "away_team_id", "game_date"),
    )


class TeamGameStat(Base):
    __tablename__ = "team_game_stats"

    game_id: Mapped[str] = mapped_column(
        ForeignKey("games.game_id", ondelete="CASCADE"), primary_key=True
    )
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), primary_key=True)
    opponent_team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), nullable=False)
    is_home: Mapped[bool] = mapped_column(Boolean, nullable=False)
    won: Mapped[bool] = mapped_column(Boolean, nullable=False)
    team_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    opponent_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    assists: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    blocks: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    steals: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    field_goals_attempted: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    field_goals_made: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    field_goal_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    three_pointers_attempted: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    three_pointers_made: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    three_point_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    free_throws_attempted: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    free_throws_made: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    free_throw_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    defensive_rebounds: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    offensive_rebounds: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    total_rebounds: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    personal_fouls: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    turnovers: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    plus_minus: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    minutes_seconds: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    __table_args__ = (
        CheckConstraint("team_id <> opponent_team_id", name="ck_team_stats_distinct_teams"),
        CheckConstraint("team_score >= 0 AND opponent_score >= 0", name="ck_team_stats_score"),
        CheckConstraint("won = (team_score > opponent_score)", name="ck_team_stats_win"),
        CheckConstraint("plus_minus = team_score - opponent_score", name="ck_team_stats_margin"),
        CheckConstraint(
            "field_goals_made BETWEEN 0 AND field_goals_attempted",
            name="ck_team_stats_fg_counts",
        ),
        CheckConstraint(
            "three_pointers_made BETWEEN 0 AND three_pointers_attempted",
            name="ck_team_stats_3p_counts",
        ),
        CheckConstraint(
            "free_throws_made BETWEEN 0 AND free_throws_attempted",
            name="ck_team_stats_ft_counts",
        ),
        CheckConstraint(
            "total_rebounds = offensive_rebounds + defensive_rebounds",
            name="ck_team_stats_rebounds",
        ),
        CheckConstraint("minutes_seconds > 0", name="ck_team_stats_minutes"),
        CheckConstraint(
            "field_goal_percentage BETWEEN 0 AND 1",
            name="ck_team_stats_fg_pct",
        ),
        CheckConstraint(
            "three_point_percentage BETWEEN 0 AND 1",
            name="ck_team_stats_3p_pct",
        ),
        CheckConstraint(
            "free_throw_percentage BETWEEN 0 AND 1",
            name="ck_team_stats_ft_pct",
        ),
        Index("ix_team_game_stats_team", "team_id", "game_id"),
        Index("ix_team_game_stats_opponent", "opponent_team_id", "game_id"),
    )


class PlayerGameStat(Base):
    __tablename__ = "player_game_stats"

    game_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.player_id"), primary_key=True)
    team_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    opponent_team_id: Mapped[int] = mapped_column(ForeignKey("teams.team_id"), nullable=False)
    is_home: Mapped[bool] = mapped_column(Boolean, nullable=False)
    won: Mapped[bool] = mapped_column(Boolean, nullable=False)
    did_play: Mapped[bool] = mapped_column(Boolean, nullable=False)
    minutes_seconds: Mapped[int | None] = mapped_column(SmallInteger)
    points: Mapped[int | None] = mapped_column(SmallInteger)
    assists: Mapped[int | None] = mapped_column(SmallInteger)
    blocks: Mapped[int | None] = mapped_column(SmallInteger)
    steals: Mapped[int | None] = mapped_column(SmallInteger)
    field_goals_attempted: Mapped[int | None] = mapped_column(SmallInteger)
    field_goals_made: Mapped[int | None] = mapped_column(SmallInteger)
    field_goal_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    three_pointers_attempted: Mapped[int | None] = mapped_column(SmallInteger)
    three_pointers_made: Mapped[int | None] = mapped_column(SmallInteger)
    three_point_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    free_throws_attempted: Mapped[int | None] = mapped_column(SmallInteger)
    free_throws_made: Mapped[int | None] = mapped_column(SmallInteger)
    free_throw_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    defensive_rebounds: Mapped[int | None] = mapped_column(SmallInteger)
    offensive_rebounds: Mapped[int | None] = mapped_column(SmallInteger)
    total_rebounds: Mapped[int | None] = mapped_column(SmallInteger)
    personal_fouls: Mapped[int | None] = mapped_column(SmallInteger)
    turnovers: Mapped[int | None] = mapped_column(SmallInteger)
    plus_minus: Mapped[int | None] = mapped_column(SmallInteger)
    availability_comment: Mapped[str | None] = mapped_column(Text)
    starting_position: Mapped[str | None] = mapped_column(String(8))

    __table_args__ = (
        ForeignKeyConstraint(
            ["game_id", "team_id"],
            ["team_game_stats.game_id", "team_game_stats.team_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("team_id <> opponent_team_id", name="ck_player_stats_distinct_teams"),
        CheckConstraint(
            "minutes_seconds IS NULL OR minutes_seconds >= 0",
            name="ck_player_stats_minutes",
        ),
        CheckConstraint(
            "(did_play AND minutes_seconds IS NOT NULL AND points IS NOT NULL "
            "AND assists IS NOT NULL AND total_rebounds IS NOT NULL) OR "
            "(NOT did_play AND minutes_seconds IS NULL AND points IS NULL "
            "AND assists IS NULL AND total_rebounds IS NULL)",
            name="ck_player_stats_played_semantics",
        ),
        CheckConstraint(
            "starting_position IS NULL OR starting_position IN ('G', 'F', 'C')",
            name="ck_player_stats_starting_position",
        ),
        CheckConstraint(
            "field_goals_made IS NULL OR field_goals_made BETWEEN 0 AND field_goals_attempted",
            name="ck_player_stats_fg_counts",
        ),
        CheckConstraint(
            "three_pointers_made IS NULL OR "
            "three_pointers_made BETWEEN 0 AND three_pointers_attempted",
            name="ck_player_stats_3p_counts",
        ),
        CheckConstraint(
            "free_throws_made IS NULL OR free_throws_made BETWEEN 0 AND free_throws_attempted",
            name="ck_player_stats_ft_counts",
        ),
        CheckConstraint(
            "total_rebounds IS NULL OR total_rebounds = offensive_rebounds + defensive_rebounds",
            name="ck_player_stats_rebounds",
        ),
        CheckConstraint(
            "field_goal_percentage IS NULL OR "
            "(field_goal_percentage >= 0 AND field_goal_percentage <= 1)",
            name="ck_player_stats_fg_pct",
        ),
        CheckConstraint(
            "three_point_percentage IS NULL OR "
            "(three_point_percentage >= 0 AND three_point_percentage <= 1)",
            name="ck_player_stats_3p_pct",
        ),
        CheckConstraint(
            "free_throw_percentage IS NULL OR "
            "(free_throw_percentage >= 0 AND free_throw_percentage <= 1)",
            name="ck_player_stats_ft_pct",
        ),
        Index("ix_player_game_stats_player", "player_id", "game_id"),
        Index("ix_player_game_stats_team", "team_id", "game_id"),
        Index("ix_player_game_stats_opponent", "opponent_team_id", "game_id"),
    )
