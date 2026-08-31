from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class NodePosition(BaseModel):
    x: float = Field(ge=-100000, le=100000)
    y: float = Field(ge=-100000, le=100000)
    width: float | None = Field(default=None, ge=80, le=2000)
    height: float | None = Field(default=None, ge=40, le=1600)
    background: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    text_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    font_size: float | None = Field(default=None, ge=9, le=32)


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
