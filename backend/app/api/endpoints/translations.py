import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.models import PaperTranslation, TranslationGlossary, TranslationJob
from app.schemas.translation import *
from app.services.ai_gateway import AIBudgetExceededError
from app.services.translation_service import TranslationService
from app.tasks.translation_tasks import enqueue_translation

router = APIRouter()


def problem(exc: Exception):
    if isinstance(exc, LookupError): return HTTPException(404, detail=str(exc))
    if isinstance(exc, PermissionError): return HTTPException(403, detail=str(exc))
    if isinstance(exc, AIBudgetExceededError): return HTTPException(402, detail=str(exc))
    return HTTPException(422, detail=str(exc))


@router.post("/papers/{paper_id}/translations/estimate", response_model=TranslationEstimateResponse)
async def estimate(paper_id: uuid.UUID, data: TranslationEstimateRequest, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await TranslationService(db).estimate(user_id, paper_id, data)
    except (LookupError, ValueError, PermissionError) as exc: raise problem(exc) from exc


@router.post("/papers/{paper_id}/translations", response_model=TranslationJobResponse, status_code=201)
async def create(paper_id: uuid.UUID, data: TranslationCreateRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try:
        job = await TranslationService(db).create(user_id, paper_id, data, process_immediately=False)
        background_tasks.add_task(enqueue_translation, user_id, job.id)
        return job
    except Exception as exc:
        if isinstance(exc, (LookupError, ValueError, PermissionError, AIBudgetExceededError)): raise problem(exc) from exc
        raise


@router.get("/papers/{paper_id}/translations", response_model=list[PaperTranslationResponse])
async def versions(paper_id: uuid.UUID, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    return list((await db.scalars(select(PaperTranslation).where(PaperTranslation.paper_id == paper_id,
        PaperTranslation.user_id == user_id).order_by(PaperTranslation.updated_at.desc()))).all())


@router.get("/papers/{paper_id}/translations/page/{page_number}", response_model=TranslationPageResponse)
async def page(paper_id: uuid.UUID, page_number: int, document_id: uuid.UUID, target_language: str = "zh-CN",
               db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await TranslationService(db).page(user_id,paper_id,document_id,page_number,target_language)
    except (LookupError, ValueError) as exc: raise problem(exc) from exc


@router.get("/translation-jobs/{job_id}", response_model=TranslationJobResponse)
async def job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    row = await db.scalar(select(TranslationJob).where(TranslationJob.id == job_id, TranslationJob.user_id == user_id))
    if not row: raise HTTPException(404, detail="Translation job not found")
    return row


@router.post("/translation-jobs/{job_id}/{action}", response_model=TranslationJobResponse)
async def transition(job_id: uuid.UUID, action: str, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    mapping={"pause":"paused","resume":"pending","cancel":"cancelled","retry":"pending"}
    if action not in mapping: raise HTTPException(404, detail="Unknown job action")
    try: return await TranslationService(db).set_status(user_id,job_id,mapping[action])
    except (LookupError,ValueError) as exc: raise problem(exc) from exc


@router.patch("/translation-blocks/{block_id}", response_model=TranslationBlockResponse)
async def update_block(block_id: uuid.UUID, data: TranslationBlockUpdate, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    try: return await TranslationService(db).update_block(user_id,block_id,data.user_translation,data.expected_revision)
    except LookupError as exc: raise HTTPException(404,detail=str(exc)) from exc
    except RuntimeError as exc: raise HTTPException(409,detail="译文已在其他页面更新，请刷新后重试") from exc


@router.get("/translation-glossary", response_model=list[GlossaryResponse])
async def glossary(paper_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    query=select(TranslationGlossary).where(TranslationGlossary.user_id==user_id)
    if paper_id: query=query.where((TranslationGlossary.scope_type=="global") | ((TranslationGlossary.scope_type=="paper") & (TranslationGlossary.scope_id==paper_id)))
    return list((await db.scalars(query.order_by(TranslationGlossary.source_term))).all())


@router.post("/translation-glossary", response_model=GlossaryResponse, status_code=201)
async def create_glossary(data: GlossaryCreate, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    if data.scope_type=="paper" and data.scope_id is None: raise HTTPException(422,detail="paper scope requires scope_id")
    row=TranslationGlossary(user_id=user_id,**data.model_dump()); db.add(row); await db.flush(); return row


@router.delete("/translation-glossary/{term_id}", status_code=204)
async def delete_glossary(term_id: uuid.UUID, db: AsyncSession = Depends(get_db), user_id: uuid.UUID = Depends(get_current_user_id)):
    row=await db.scalar(select(TranslationGlossary).where(TranslationGlossary.id==term_id,TranslationGlossary.user_id==user_id))
    if not row: raise HTTPException(404,detail="Glossary term not found")
    await db.delete(row); return Response(status_code=204)
