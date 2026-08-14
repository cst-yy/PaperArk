import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_current_user_id, get_db
from app.models import Folder, PaperFolder
from pydantic import BaseModel

router = APIRouter()


class FolderCreate(BaseModel):
    name: str
    parent_id: uuid.UUID | None = None
    color: str | None = None
    icon: str | None = None


class FolderUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    icon: str | None = None
    parent_id: uuid.UUID | None = None


class FolderResponse(BaseModel):
    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None = None
    color: str | None = None
    icon: str | None = None
    sort_order: int
    paper_count: int = 0
    children: list["FolderResponse"] = []

    model_config = {"from_attributes": True}


async def _count_papers(db: AsyncSession, folder_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count(PaperFolder.id)).where(PaperFolder.folder_id == folder_id)
    )
    return result.scalar() or 0


@router.get("/", response_model=list[FolderResponse])
async def list_folders(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    stmt = (
        select(Folder)
        .where(Folder.user_id == user_id)
        .order_by(Folder.sort_order, Folder.name)
    )
    result = await db.execute(stmt)
    folders = result.scalars().all()

    counts = {}
    for f in folders:
        counts[f.id] = await _count_papers(db, f.id)

    folder_map: dict[uuid.UUID, FolderResponse] = {}
    roots: list[FolderResponse] = []

    for f in folders:
        resp = FolderResponse(
            id=f.id,
            name=f.name,
            parent_id=f.parent_id,
            color=f.color,
            icon=f.icon,
            sort_order=f.sort_order,
            paper_count=counts.get(f.id, 0),
        )
        folder_map[f.id] = resp

    for f in folders:
        resp = folder_map[f.id]
        if f.parent_id and f.parent_id in folder_map:
            folder_map[f.parent_id].children.append(resp)
        else:
            roots.append(resp)

    return roots


@router.post("/", response_model=FolderResponse)
async def create_folder(
    data: FolderCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    folder = Folder(
        user_id=user_id,
        name=data.name,
        parent_id=data.parent_id,
        color=data.color,
        icon=data.icon,
    )
    db.add(folder)
    await db.flush()
    return FolderResponse(
        id=folder.id,
        name=folder.name,
        parent_id=folder.parent_id,
        color=folder.color,
        icon=folder.icon,
        sort_order=folder.sort_order,
    )


@router.patch("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: uuid.UUID,
    data: FolderUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    folder = await db.get(Folder, folder_id)
    if not folder or folder.user_id != user_id:
        raise HTTPException(status_code=404, detail="Folder not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(folder, key, value)

    await db.flush()
    return FolderResponse(
        id=folder.id,
        name=folder.name,
        parent_id=folder.parent_id,
        color=folder.color,
        icon=folder.icon,
        sort_order=folder.sort_order,
    )


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    folder = await db.get(Folder, folder_id)
    if not folder or folder.user_id != user_id:
        raise HTTPException(status_code=404, detail="Folder not found")
    await db.delete(folder)
    return {"message": "Folder deleted"}


# ─────────── Folder-centric paper management ───────────

@router.post("/{folder_id}/papers/{paper_id}")
async def add_paper_to_folder(
    folder_id: uuid.UUID,
    paper_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    folder = await db.get(Folder, folder_id)
    if not folder or folder.user_id != user_id:
        raise HTTPException(status_code=404, detail="Folder not found")

    existing = await db.execute(
        select(PaperFolder).where(
            PaperFolder.folder_id == folder_id,
            PaperFolder.paper_id == paper_id,
        )
    )
    if existing.scalars().first():
        return {"message": "Already in folder"}

    db.add(PaperFolder(folder_id=folder_id, paper_id=paper_id))
    await db.flush()
    return {"message": "Added to folder"}


@router.delete("/{folder_id}/papers/{paper_id}")
async def remove_paper_from_folder(
    folder_id: uuid.UUID,
    paper_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    folder = await db.get(Folder, folder_id)
    if not folder or folder.user_id != user_id:
        raise HTTPException(status_code=404, detail="Folder not found")

    result = await db.execute(
        select(PaperFolder).where(
            PaperFolder.folder_id == folder_id,
            PaperFolder.paper_id == paper_id,
        )
    )
    pf = result.scalars().first()
    if pf:
        await db.delete(pf)
    return {"message": "Removed from folder"}
