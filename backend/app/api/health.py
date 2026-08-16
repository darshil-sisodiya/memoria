"""Health endpoint."""

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text


class HealthResponse(BaseModel):
    status: str
    service: str
    database: str


router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    """Return service and database connectivity status."""

    with request.app.state.engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return HealthResponse(status="ok", service="memoria-api", database="ok")

