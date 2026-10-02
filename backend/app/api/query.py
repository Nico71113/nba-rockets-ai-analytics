from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.database import get_session
from backend.app.orchestration.router import OllamaIntentRouter
from backend.app.orchestration.service import answer_question
from backend.app.schemas import QueryRequest, QueryResponse

router = APIRouter(prefix="/api/v1", tags=["query"])
SessionDependency = Annotated[Session, Depends(get_session)]


@lru_cache
def get_intent_router() -> OllamaIntentRouter:
    return OllamaIntentRouter(get_settings())


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest, session: SessionDependency) -> QueryResponse:
    return answer_question(
        session,
        question=request.question.strip(),
        router=get_intent_router(),
    )
