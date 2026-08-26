import uuid
import pytest

from app.core.exceptions import MemoNotFoundError, PaperNotFoundError, RevisionConflictError, TodoNotFoundError
from app.models import Paper, User
from app.schemas.folder import FolderCreate, FolderUpdate
from app.schemas.memo import MemoCreate, MemoUpdate
from app.schemas.todo import TodoCreate, TodoUpdate
from app.services.folder_service import FolderService
from app.services.memo_service import MemoService
from app.services.todo_service import TodoService

async def user(session,name):
    item=User(id=uuid.uuid4(),username=name,email=f"{name}@example.com",password_hash="");session.add(item);await session.flush();return item.id

@pytest.mark.asyncio
async def test_todo_crud_completion_revision_and_scope(session):
    owner=await user(session,"todo-owner");other=await user(session,"todo-other");paper=Paper(user_id=owner,title="Owned paper");session.add(paper);await session.flush();service=TodoService(session)
    item=await service.create(owner,TodoCreate(title="  Run ablation  ",priority="high",related_paper_id=paper.id))
    assert item.title=="Run ablation" and item.revision==1
    done=await service.update(owner,item.id,TodoUpdate(expected_revision=1,completed=True))
    assert done.completed and done.completed_at and done.revision==2
    with pytest.raises(RevisionConflictError): await service.update(owner,item.id,TodoUpdate(expected_revision=1,title="stale"))
    with pytest.raises(TodoNotFoundError): await service.delete(other,item.id)
    foreign=Paper(user_id=other,title="Foreign paper");session.add(foreign);await session.flush()
    with pytest.raises(PaperNotFoundError): await service.create(owner,TodoCreate(title="bad relation",related_paper_id=foreign.id))
    await service.delete(owner,item.id)

@pytest.mark.asyncio
async def test_memo_crud_pin_order_revision_and_scope(session):
    owner=await user(session,"memo-owner");other=await user(session,"memo-other");service=MemoService(session)
    first=await service.create(owner,MemoCreate(content=" First idea "));second=await service.create(owner,MemoCreate(content="Pinned",pinned=True,color="#8b5cf6"))
    assert [x.id for x in await service.list(owner,20)][0]==second.id
    changed=await service.update(owner,first.id,MemoUpdate(expected_revision=1,content="Refined",color="#3b82f6"))
    assert changed.content=="Refined" and changed.revision==2
    with pytest.raises(RevisionConflictError): await service.update(owner,first.id,MemoUpdate(expected_revision=1,pinned=True))
    with pytest.raises(MemoNotFoundError): await service.delete(other,first.id)

@pytest.mark.asyncio
async def test_folder_rename_color_clear_revision_and_duplicate(session):
    owner=await user(session,"folder-owner");other=await user(session,"folder-other");service=FolderService(session)
    folder=await service.create(owner,FolderCreate(name="Reading"));updated=await service.update(owner,folder.id,FolderUpdate(expected_revision=1,name="Archive",color="#3b82f6"))
    assert updated.id==folder.id and updated.name=="Archive" and updated.revision==2
    cleared=await service.update(owner,folder.id,FolderUpdate(expected_revision=2,color=None));assert cleared.color is None
    with pytest.raises(RevisionConflictError): await service.update(owner,folder.id,FolderUpdate(expected_revision=1,name="stale"))
    with pytest.raises(Exception): await service.update(other,folder.id,FolderUpdate(expected_revision=3,name="foreign"))
    await service.create(owner,FolderCreate(name="Existing"))
    with pytest.raises(ValueError): await service.update(owner,folder.id,FolderUpdate(expected_revision=3,name=" existing "))
