from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatSessionCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    title: str = Field("新对话", min_length=1, max_length=255)
    scope_type: Literal["selection", "page", "section", "paper"] = "paper"
    scope_snapshot: dict | None = None
    model_id: UUID | None = None


class ChatSessionUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    model_id: UUID | None = None


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    id: UUID
    paper_id: UUID
    title: str
    scope_type: str
    scope_snapshot: dict | None
    model_id: UUID | None
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    scope_type: Literal["selection", "page", "section", "paper"] | None = None
    page_number: int | None = Field(None, ge=1)
    section_id: UUID | None = None
    selected_text: str | None = Field(None, max_length=12000)


class MessageCitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    paper_id: UUID
    section_id: UUID | None
    chunk_id: UUID | None
    page_block_id: UUID | None
    page_number: int | None
    quote_text: str
    bounding_box: dict | None
    citation_order: int


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    session_id: UUID
    role: str
    content: str
    status: str
    request_record_id: UUID | None
    input_scope_snapshot: dict | None
    created_at: datetime
    citations: list[MessageCitationResponse] = []


class ChatTurnResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
