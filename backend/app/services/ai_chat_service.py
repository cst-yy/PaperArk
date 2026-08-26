import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import (AIChatMessage, AIChatSession, AIMessageCitation, Chunk,
                        Document, PageBlock, Paper, Section)
from app.schemas.ai_chat import ChatMessageCreate, ChatSessionCreate
from app.schemas.note import NoteCreate
from app.schemas.rag import RAGContextRequest, RAGSource
from app.services.ai_gateway import AIGateway
from app.services.citation_validator import CitationValidator
from app.services.grounded_prompt import GroundedPromptBuilder
from app.services.note_service import NoteService
from app.services.rag_service import RAGService


class AIChatService:
    def __init__(self, db: AsyncSession): self.db=db

    async def create_session(self,user_id,paper_id,data:ChatSessionCreate):
        await self._paper(user_id,paper_id)
        row=AIChatSession(user_id=user_id,paper_id=paper_id,title=data.title,scope_type=data.scope_type,
            scope_snapshot=data.scope_snapshot,model_id=data.model_id)
        self.db.add(row); await self.db.flush(); return row

    async def sessions(self,user_id,paper_id):
        await self._paper(user_id,paper_id)
        return list((await self.db.scalars(select(AIChatSession).where(AIChatSession.user_id==user_id,
            AIChatSession.paper_id==paper_id).order_by(AIChatSession.updated_at.desc()))).all())

    async def session(self,user_id,session_id):
        row=await self.db.scalar(select(AIChatSession).where(AIChatSession.id==session_id,AIChatSession.user_id==user_id))
        if not row: raise LookupError("Chat session not found")
        return row

    async def messages(self,user_id,session_id):
        await self.session(user_id,session_id)
        return list((await self.db.scalars(select(AIChatMessage).where(AIChatMessage.session_id==session_id)
            .options(selectinload(AIChatMessage.citations)).order_by(AIChatMessage.created_at,AIChatMessage.id))).all())

    async def ask(self,user_id,session_id,data:ChatMessageCreate):
        session=await self.session(user_id,session_id)
        paper=await self._paper(user_id,session.paper_id)
        if paper.ai_access_policy=="disabled": raise PermissionError("该论文已禁止 AI 处理")
        scope=data.scope_type or session.scope_type
        snapshot={"scope_type":scope,"page_number":data.page_number,"section_id":str(data.section_id) if data.section_id else None}
        user=AIChatMessage(session_id=session.id,role="user",content=data.content.strip(),input_scope_snapshot=snapshot)
        self.db.add(user); await self.db.flush()
        sources=await self._sources(user_id,paper.id,data,scope)
        if not sources:
            assistant=AIChatMessage(session_id=session.id,role="assistant",content="当前范围内没有足够的论文原文证据来回答这个问题。",status="completed",input_scope_snapshot=snapshot)
            self.db.add(assistant); session.last_message_at=datetime.now(timezone.utc); await self.db.flush()
            return user,assistant
        messages=GroundedPromptBuilder().build(data.content,sources)
        result,record=await AIGateway(self.db).generate(user_id=user_id,feature="reader_qa",operation="answer_question",
            messages=messages,max_tokens=settings.AI_MAX_OUTPUT_TOKENS,temperature=settings.AI_TEMPERATURE,
            paper_id=paper.id,model_id=session.model_id,context_type="chat_session",context_id=session.id)
        validated=CitationValidator().validate(result.text,sources)
        assistant=AIChatMessage(session_id=session.id,role="assistant",content=validated.answer,status="completed",
            request_record_id=record.id,input_scope_snapshot=snapshot)
        self.db.add(assistant); await self.db.flush()
        source_map={f"S{i}":source for i,source in enumerate(sources,1)}
        for order,citation in enumerate(validated.citations,1):
            source=source_map[citation.label]
            chunk_id=self._chunk_id(source.source_key)
            block=await self._nearest_block(paper.id,source.page_start,source.content)
            self.db.add(AIMessageCitation(message_id=assistant.id,paper_id=paper.id,section_id=source.section_id,
                chunk_id=chunk_id,page_block_id=block.id if block else None,page_number=source.page_start,
                quote_text=source.content[:1000],bounding_box=block.bounding_box if block else None,citation_order=order))
        session.last_message_at=datetime.now(timezone.utc); await self.db.flush()
        return user,await self._message(assistant.id)

    async def save_as_note(self,user_id,message_id):
        message=await self.db.scalar(select(AIChatMessage).join(AIChatSession).where(AIChatMessage.id==message_id,
            AIChatSession.user_id==user_id,AIChatMessage.role=="assistant"))
        if not message: raise LookupError("Assistant message not found")
        session=await self.db.get(AIChatSession,message.session_id); assert session
        return await NoteService(self.db).create_note(user_id,NoteCreate(paper_id=session.paper_id,
            title=f"AI 问答：{session.title}"[:500],content_markdown=message.content,note_type="paper"))

    async def _sources(self,user_id,paper_id,data,scope):
        if scope=="selection" and data.selected_text:
            return [RAGSource(source_key="selection",source_type="paper_chunk",paper_id=paper_id,title="当前选区",
                content=data.selected_text,retrieval_method="lexical",estimated_tokens=max(1,len(data.selected_text)//4),page_start=data.page_number,page_end=data.page_number)]
        if scope in {"page","section"}:
            query=select(PageBlock).where(PageBlock.paper_id==paper_id,PageBlock.block_type.not_in({"header","footer"}))
            if scope=="page":
                if not data.page_number: raise ValueError("page_number is required")
                query=query.where(PageBlock.page_number==data.page_number)
            else:
                if not data.section_id: raise ValueError("section_id is required")
                section=await self.db.scalar(select(Section).join(Document, Section.document_id==Document.id)
                    .join(Paper, Document.paper_id==Paper.id).where(Section.id==data.section_id,Paper.id==paper_id))
                if not section: raise ValueError("section is outside paper")
                query=query.where(PageBlock.page_number.between(section.page_start,section.page_end))
            blocks=list((await self.db.scalars(query.order_by(PageBlock.reading_order).limit(60))).all())
            return [RAGSource(source_key=f"page_block:{b.id}",source_type="paper_chunk",paper_id=paper_id,
                document_id=b.document_id,section_id=b.section_id,title=f"第 {b.page_number} 页",content=b.source_text,
                retrieval_method="lexical",estimated_tokens=max(1,len(b.source_text)//4),page_start=b.page_number,page_end=b.page_number) for b in blocks]
        context=await RAGService(self.db).build_context(user_id,RAGContextRequest(query=data.content,mode="hybrid",paper_id=paper_id))
        return context.sources

    async def _paper(self,user_id,paper_id):
        row=await self.db.scalar(select(Paper).where(Paper.id==paper_id,Paper.user_id==user_id))
        if not row: raise LookupError("Paper not found")
        return row

    async def _message(self,message_id):
        return await self.db.scalar(select(AIChatMessage).where(AIChatMessage.id==message_id).options(selectinload(AIChatMessage.citations)))

    async def _nearest_block(self,paper_id,page,text):
        if not page:return None
        return await self.db.scalar(select(PageBlock).where(PageBlock.paper_id==paper_id,PageBlock.page_number==page).order_by(PageBlock.reading_order))

    @staticmethod
    def _chunk_id(key):
        if key.startswith("chunk:"):
            try:return uuid.UUID(key.split(":",1)[1])
            except ValueError:return None
        return None
