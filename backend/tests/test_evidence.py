from __future__ import annotations

import pytest
from fastapi import HTTPException

from backend.app.api.evidence import evidence_games
from evals.tests.conftest import eval_session as eval_session
from evals.tests.conftest import eval_snapshot as eval_snapshot


def test_evidence_games_returns_auditable_game_rows(eval_session):
    rows = evidence_games("eval-004,eval-001,eval-004", eval_session)

    assert [row.game_id for row in rows] == ["eval-001", "eval-004"]
    assert rows[0].home_team == "Houston Rockets"
    assert rows[0].away_team == "Oklahoma City Thunder"
    assert rows[0].winner == "Houston Rockets"
    assert rows[0].home_score == 110
    assert rows[0].away_score == 100


def test_evidence_games_limits_bulk_inspection(eval_session):
    with pytest.raises(HTTPException, match="At most 100 game IDs"):
        evidence_games(",".join(f"game-{index}" for index in range(101)), eval_session)
