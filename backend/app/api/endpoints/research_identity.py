import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_current_user_id, get_db
from app.models import Author, Paper, PaperAuthor, ResearchIdentity
from app.schemas.research_identity import (
    MyPaperStats, ResearchIdentityCandidate, ResearchIdentityResponse,
    ResearchIdentityUpdate,
)

router = APIRouter()


def _response(row: ResearchIdentity) -> ResearchIdentityResponse:
    return ResearchIdentityResponse(
        id=row.id, author_id=row.author_id, author_name=row.author.name,
        display_name=row.display_name, orcid=row.orcid, email=row.email,
        created_at=row.created_at, updated_at=row.updated_at,
    )


@router.get("", response_model=ResearchIdentityResponse | None)
async def get_identity(db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    row = await db.scalar(
        select(ResearchIdentity)
        .where(ResearchIdentity.user_id == user_id)
        .options(selectinload(ResearchIdentity.author))
    )
    return _response(row) if row else None


@router.get("/candidates", response_model=list[ResearchIdentityCandidate])
async def candidates(db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    rows = (await db.execute(
        select(Author.id, Author.name, Author.orcid, Author.affiliation,
               func.count(distinct(Paper.id)).label("paper_count"))
        .join(PaperAuthor, PaperAuthor.author_id == Author.id)
        .join(Paper, Paper.id == PaperAuthor.paper_id)
        .where(Paper.user_id == user_id)
        .group_by(Author.id).order_by(func.count(distinct(Paper.id)).desc(), Author.name)
    )).all()
    return [ResearchIdentityCandidate(author_id=row.id, name=row.name, orcid=row.orcid,
        affiliation=row.affiliation, paper_count=row.paper_count) for row in rows]


@router.put("", response_model=ResearchIdentityResponse)
async def set_identity(data: ResearchIdentityUpdate, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    permitted = await db.scalar(select(PaperAuthor.id).join(Paper, Paper.id == PaperAuthor.paper_id).where(
        Paper.user_id == user_id, PaperAuthor.author_id == data.author_id).limit(1))
    if permitted is None:
        raise HTTPException(422, detail="只能绑定当前论文库中出现的作者身份")
    row = await db.scalar(select(ResearchIdentity).where(ResearchIdentity.user_id == user_id).with_for_update())
    author = await db.get(Author, data.author_id)
    if row:
        row.author_id = data.author_id
        row.display_name = (data.display_name or author.name).strip() if "display_name" in data.model_fields_set else author.name
        row.orcid = data.orcid if "orcid" in data.model_fields_set else author.orcid
        if "email" in data.model_fields_set: row.email = data.email
    else:
        row = ResearchIdentity(user_id=user_id, author_id=data.author_id,
            display_name=(data.display_name or author.name).strip(),
            orcid=data.orcid if data.orcid is not None else author.orcid,
            email=data.email); db.add(row)
    await db.flush(); await db.refresh(row, attribute_names=["author"])
    return _response(row)


@router.delete("", status_code=204)
async def clear_identity(db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    row = await db.scalar(select(ResearchIdentity).where(ResearchIdentity.user_id == user_id))
    if row: await db.delete(row)
    return Response(status_code=204)


@router.get("/stats", response_model=MyPaperStats)
async def stats(db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    identity = await db.scalar(select(ResearchIdentity).where(ResearchIdentity.user_id == user_id))
    if not identity: return MyPaperStats(total=0, first_or_co_first=0, corresponding=0, other=0)
    result = (await db.execute(select(
        func.count(distinct(PaperAuthor.paper_id)),
        func.count(distinct(PaperAuthor.paper_id)).filter((PaperAuthor.author_order == 0) | PaperAuthor.is_co_first.is_(True)),
        func.count(distinct(PaperAuthor.paper_id)).filter(PaperAuthor.is_corresponding.is_(True)),
        func.count(distinct(PaperAuthor.paper_id)).filter(PaperAuthor.author_order > 0, PaperAuthor.is_co_first.is_(False), PaperAuthor.is_corresponding.is_(False)),
    ).join(Paper, Paper.id == PaperAuthor.paper_id).where(Paper.user_id == user_id, PaperAuthor.author_id == identity.author_id))).one()
    return MyPaperStats(total=result[0], first_or_co_first=result[1], corresponding=result[2], other=result[3])
