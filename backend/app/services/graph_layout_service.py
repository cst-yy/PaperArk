import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GraphLayout
from app.schemas.graph_layout import GraphLayoutResponse, GraphLayoutSave


class GraphLayoutService:
    def __init__(self, db: AsyncSession): self.db = db

    async def get(self, user_id: uuid.UUID, graph_type: str, scope_key: str):
        item = await self.db.scalar(select(GraphLayout).where(GraphLayout.user_id == user_id,
            GraphLayout.graph_type == graph_type, GraphLayout.scope_key == scope_key))
        return self._response(item) if item else None

    async def save(self, user_id: uuid.UUID, data: GraphLayoutSave):
        item = await self.db.scalar(select(GraphLayout).where(GraphLayout.user_id == user_id,
            GraphLayout.graph_type == data.graph_type, GraphLayout.scope_key == data.scope_key).with_for_update())
        positions = {key: value.model_dump() for key, value in data.positions.items()}
        if item is None:
            item = GraphLayout(user_id=user_id, graph_type=data.graph_type,
                scope_key=data.scope_key, layout_json=positions); self.db.add(item)
        else: item.layout_json = positions
        await self.db.flush()
        await self.db.refresh(item)
        return self._response(item)

    @staticmethod
    def _response(item):
        return GraphLayoutResponse(id=item.id, graph_type=item.graph_type, scope_key=item.scope_key,
            positions=item.layout_json, updated_at=item.updated_at)
