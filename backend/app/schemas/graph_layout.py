from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class NodePosition(BaseModel):
    x: float = Field(ge=-100000, le=100000)
    y: float = Field(ge=-100000, le=100000)


class GraphLayoutSave(BaseModel):
    graph_type: Literal["citation", "knowledge", "mind_map"]
    scope_key: str = Field(min_length=1, max_length=500)
    positions: dict[str, NodePosition] = Field(default_factory=dict)

    @field_validator("positions")
    @classmethod
    def validate_positions(cls, value):
        if len(value) > 500: raise ValueError("at most 500 node positions may be saved")
        for key in value:
            if not key or len(key) > 200: raise ValueError("invalid node key")
        return value


class GraphLayoutResponse(GraphLayoutSave):
    id: UUID
    updated_at: datetime
