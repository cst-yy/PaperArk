import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.core.database import get_current_user_id
from app.schemas.dashboard import DashboardResponse, ReadingTrendResponse
from app.services.dashboard_service import DashboardService, get_dashboard_service

router = APIRouter()


@router.get("/", response_model=DashboardResponse)
async def get_dashboard(
    topic_days: Literal["7", "30"] = Query("30"),
    topic_limit: Literal["20", "50"] = Query("20"),
    service: DashboardService = Depends(get_dashboard_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await service.get_dashboard(user_id, int(topic_days), int(topic_limit))


@router.get("/reading-trend", response_model=ReadingTrendResponse)
async def get_reading_trend(
    days: Literal["7", "30", "90"] = Query("7"),
    service: DashboardService = Depends(get_dashboard_service),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    return await service.reading_trend(user_id, int(days))
