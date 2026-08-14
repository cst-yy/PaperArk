import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import InvalidNoteError, NoteNotFoundError
from app.models import Annotation, Document, NoteEvidence, Paper, User
from app.schemas.note import NoteCreate
from app.schemas.research_note import ContributionInput, ExperimentInput, ResearchProfileAggregate
from app.services.note_service import NoteService
from app.services.research_note_service import ResearchNoteService

async def setup(session: AsyncSession):
    user=User(id=uuid.uuid4(),username="research",email="research@profile.test",password_hash=""); other=User(id=uuid.uuid4(),username="other-research",email="other@profile.test",password_hash="")
    session.add_all([user,other]); await session.flush()
    paper=Paper(user_id=user.id,title="Research Paper",status="ready"); session.add(paper); await session.flush()
    doc=Document(paper_id=paper.id,file_path="pdfs/research.pdf",parse_status="ready"); session.add(doc); await session.flush()
    anns=[Annotation(user_id=user.id,paper_id=paper.id,document_id=doc.id,type="highlight",page_number=i+1,selected_text=f"evidence {i}",position_data={"kind":"text","rects":[{"x":.1,"y":.1,"width":.2,"height":.1}]}) for i in range(2)]
    session.add_all(anns); await session.flush()
    note=await NoteService(session).create_note(user.id,NoteCreate(paper_id=paper.id,title="Structured",note_type="research",annotation_ids=[x.id for x in anns]))
    return user,other,note

def payload(evidence_ids):
    return ResearchProfileAggregate(background="background",research_problem="problem",method_summary="method",future_work="extend to new domains",contributions=[ContributionInput(client_id="c1",problem="p",prior_limitation="l",innovation="i",solution="s",evidence_ids=[evidence_ids[0]])],experiments=[ExperimentInput(client_id="e1",task="classification",datasets=["CIFAR-10"],baselines=["FedAvg"],metrics=["Accuracy"],result="better",conclusion="supports",supports_contribution_client_ids=["c1"],evidence_ids=[evidence_ids[1]])])

@pytest.mark.asyncio
async def test_research_profile_aggregate_roundtrip_and_structure_deletion(session: AsyncSession):
    user,_,note=await setup(session); evidence=[x.id for x in note.evidence]
    saved=await ResearchNoteService(session).save(user.id,note.id,payload(evidence))
    assert saved.background=="background" and saved.future_work=="extend to new domains" and saved.contributions[0].evidence_ids==[evidence[0]]
    assert saved.experiments[0].datasets==["CIFAR-10"] and saved.experiments[0].contribution_ids==[saved.contributions[0].id]
    empty=payload(evidence); empty.contributions=[]; empty.experiments=[]
    result=await ResearchNoteService(session).save(user.id,note.id,empty)
    assert not result.contributions and not result.experiments
    assert len((await NoteService(session).get_note(user.id,note.id)).evidence)==2

@pytest.mark.asyncio
async def test_invalid_foreign_note_evidence_rolls_back_entire_profile(session: AsyncSession):
    user,_,note=await setup(session); evidence=[x.id for x in note.evidence]
    user_id,note_id,paper_id,annotation_id=user.id,note.id,note.paper_id,note.evidence[0].annotation_id
    service=ResearchNoteService(session); original=await service.save(user_id,note_id,payload(evidence)); await session.commit()
    foreign_note=await NoteService(session).create_note(user_id,NoteCreate(paper_id=paper_id,title="Other",note_type="research",annotation_ids=[annotation_id]))
    invalid=payload(evidence); invalid.contributions[0].evidence_ids=[foreign_note.evidence[0].id]
    with pytest.raises(InvalidNoteError): await service.save(user_id,note_id,invalid)
    await session.rollback(); persisted=await ResearchNoteService(session).get(user_id,note_id)
    assert persisted and persisted.background==original.background and persisted.contributions[0].innovation=="i"

@pytest.mark.asyncio
async def test_profile_rejects_non_research_and_foreign_note(session: AsyncSession):
    user,other,note=await setup(session)
    general=await NoteService(session).create_note(user.id,NoteCreate(title="General"))
    with pytest.raises(InvalidNoteError): await ResearchNoteService(session).save(user.id,general.id,ResearchProfileAggregate())
    with pytest.raises(NoteNotFoundError): await ResearchNoteService(session).get(other.id,note.id)
