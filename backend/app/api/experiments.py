from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.database import get_session
from backend.app.experiments.three_point_forecast import run_three_point_forecast
from backend.app.schemas import ThreePointForecastResponse

router = APIRouter(prefix="/api/v1/experiments", tags=["experiments"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/three-point-forecast", response_model=ThreePointForecastResponse)
def three_point_forecast_endpoint(session: SessionDependency) -> ThreePointForecastResponse:
    return run_three_point_forecast(session, season_id=get_settings().season_id)
