import uuid
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import FolderNotFoundError, RevisionConflictError
from app.models import Folder
from app.schemas.folder import FolderCreate, FolderUpdate

class FolderService:
    def __init__(self, db: AsyncSession): self.db=db
    async def create(self,user_id:uuid.UUID,data:FolderCreate):
        await self._validate(user_id,data.name,data.parent_id)
        item=Folder(user_id=user_id,**data.model_dump());self.db.add(item);await self.db.flush();return item
    async def update(self,user_id:uuid.UUID,item_id:uuid.UUID,data:FolderUpdate):
        current=await self.db.scalar(select(Folder).where(Folder.id==item_id,Folder.user_id==user_id))
        if not current: raise FolderNotFoundError("Folder not found")
        values=data.model_dump(exclude_unset=True,exclude={"expected_revision"})
        await self._validate(user_id,values.get("name",current.name),values.get("parent_id",current.parent_id),exclude_id=item_id)
        result=await self.db.execute(update(Folder).where(Folder.id==item_id,Folder.user_id==user_id,Folder.revision==data.expected_revision).values(**values,revision=Folder.revision+1).returning(Folder))
        item=result.scalar_one_or_none()
        if not item: raise RevisionConflictError("Folder changed in another tab")
        return item
    async def delete(self,user_id:uuid.UUID,item_id:uuid.UUID):
        item=await self.db.scalar(select(Folder).where(Folder.id==item_id,Folder.user_id==user_id))
        if not item: raise FolderNotFoundError("Folder not found")
        await self.db.delete(item)
    async def _validate(self,user_id,name,parent_id,exclude_id=None):
        if parent_id and not await self.db.scalar(select(Folder.id).where(Folder.id==parent_id,Folder.user_id==user_id)): raise FolderNotFoundError("Parent folder not found")
        stmt=select(Folder.id).where(Folder.user_id==user_id,func.lower(func.trim(Folder.name))==name.strip().lower(),Folder.parent_id==parent_id)
        if exclude_id: stmt=stmt.where(Folder.id!=exclude_id)
        if await self.db.scalar(stmt): raise ValueError("Folder name already exists")
