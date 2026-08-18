import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GraphLayout(Base):
    __tablename__ = "graph_layouts"
    __table_args__ = (
        UniqueConstraint("user_id", "graph_type", "scope_key", name="uq_graph_layout_scope"),
        CheckConstraint("graph_type IN ('citation','knowledge','mind_map')", name="ck_graph_layout_type"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    graph_type: Mapped[str] = mapped_column(String(20), index=True)
    scope_key: Mapped[str] = mapped_column(String(500))
    layout_json: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
