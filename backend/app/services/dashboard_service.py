import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard import (
    DashboardBackup, DashboardOverview, DashboardRecentNote, DashboardRecentPaper,
    DashboardRecentReading, DashboardResponse, DashboardTopicStat,
    ReadingTrendDay, ReadingTrendResponse, ReadingTrendSummary,
)
from app.services.backup_service import BackupService


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DashboardRepository(db)

    async def get_dashboard(self, user_id: uuid.UUID, topic_days: int = 30, topic_limit: int = 20) -> DashboardResponse:
        total, reading, finished, notes = await self.repo.overview(user_id)
        recent_reading = await self.repo.recent_reading(user_id)
        recent_papers = await self.repo.recent_papers(user_id)
        recent_notes = await self.repo.recent_notes(user_id)
        topic_since = datetime.now(UTC) - timedelta(days=topic_days)
        tags = await self.repo.tags(user_id, topic_since, topic_limit)
        keywords = await self.repo.keywords(user_id, topic_since, topic_limit)
        backups = await BackupService(self.db).list_backups()
        return DashboardResponse(
            overview=DashboardOverview(
                total_papers=total, reading_papers=reading,
                finished_papers=finished, research_notes=notes,
            ),
            recent_reading=[DashboardRecentReading(**item) for item in recent_reading],
            recent_papers=[DashboardRecentPaper(**item) for item in recent_papers],
            recent_notes=[DashboardRecentNote(**item) for item in recent_notes],
            tags=[DashboardTopicStat(**item) for item in tags],
            keywords=[DashboardTopicStat(**item) for item in keywords],
            backup=DashboardBackup(last_backup_at=backups[0].created_at if backups else None),
        )

    async def reading_trend(self, user_id: uuid.UUID, days: int) -> ReadingTrendResponse:
        today = datetime.now(UTC).date()
        start = today - timedelta(days=days - 1)
        counts = {row.activity_date: row for row in await self.repo.reading_trend(user_id, start)}
        daily = [
            ReadingTrendDay(
                date=start + timedelta(days=index),
                papers_read=counts[start + timedelta(days=index)].papers_read if start + timedelta(days=index) in counts else 0,
                reading_time_seconds=counts[start + timedelta(days=index)].reading_time_seconds if start + timedelta(days=index) in counts else 0,
            )
            for index in range(days)
        ]
        return ReadingTrendResponse(
            days=days,
            daily=daily,
            summary=ReadingTrendSummary(
                papers_read=sum(item.papers_read for item in daily),
                active_days=sum(1 for item in daily if item.papers_read > 0),
                reading_time_seconds=sum(item.reading_time_seconds for item in daily),
            ),
        )


def get_dashboard_service(db: AsyncSession = Depends(get_db)) -> DashboardService:
    return DashboardService(db)
