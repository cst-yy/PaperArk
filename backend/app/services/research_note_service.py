import uuid
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.exceptions import InvalidNoteError, NoteNotFoundError
from app.models import ContributionEvidence, ExperimentContribution, ExperimentEvidence, Note, NoteEvidence, ResearchContribution, ResearchExperiment, ResearchNoteProfile
from app.schemas.research_note import ContributionResponse, ExperimentResponse, ResearchProfileAggregate, ResearchProfileResponse

class ResearchNoteService:
    def __init__(self, db: AsyncSession): self.db = db
    async def _note(self, user_id: uuid.UUID, note_id: uuid.UUID) -> Note:
        note = await self.db.scalar(select(Note).where(Note.id == note_id, Note.user_id == user_id))
        if not note: raise NoteNotFoundError("Note not found")
        if note.note_type != "research" or note.paper_id is None: raise InvalidNoteError("Structured profiles require a paper-scoped research note")
        return note
    async def get(self, user_id: uuid.UUID, note_id: uuid.UUID) -> ResearchProfileResponse | None:
        await self._note(user_id, note_id)
        profile = await self._profile(note_id)
        return self._response(profile) if profile else None
    async def save(self, user_id: uuid.UUID, note_id: uuid.UUID, data: ResearchProfileAggregate) -> ResearchProfileResponse:
        await self._note(user_id, note_id)
        evidence_ids = {value for item in [*data.contributions, *data.experiments] for value in item.evidence_ids}
        if evidence_ids:
            owned = set((await self.db.scalars(select(NoteEvidence.id).where(NoteEvidence.note_id == note_id, NoteEvidence.id.in_(evidence_ids)))).all())
            if owned != evidence_ids: raise InvalidNoteError("Structured items may only reference NoteEvidence from this note")
        profile = await self._profile(note_id)
        if not profile:
            profile = ResearchNoteProfile(note_id=note_id); self.db.add(profile); await self.db.flush()
        for field in ("background","prior_work_limitations","research_problem","method_summary","results_summary","conclusion","limitations","my_thoughts"): setattr(profile, field, getattr(data, field))
        await self.db.execute(delete(ResearchContribution).where(ResearchContribution.research_note_id == profile.id))
        await self.db.execute(delete(ResearchExperiment).where(ResearchExperiment.research_note_id == profile.id))
        await self.db.flush()
        contribution_map: dict[str, ResearchContribution] = {}
        for index, item in enumerate(data.contributions):
            model = ResearchContribution(research_note_id=profile.id, order_index=index, problem=item.problem, prior_limitation=item.prior_limitation, innovation=item.innovation, solution=item.solution, evidence_summary=item.evidence_summary)
            self.db.add(model); await self.db.flush(); contribution_map[item.client_id] = model
            self.db.add_all([ContributionEvidence(contribution_id=model.id, note_evidence_id=value) for value in item.evidence_ids])
        for index, item in enumerate(data.experiments):
            model = ResearchExperiment(research_note_id=profile.id, order_index=index, task=item.task, datasets_json=item.datasets, baselines_json=item.baselines, metrics_json=item.metrics, result=item.result, conclusion=item.conclusion)
            self.db.add(model); await self.db.flush()
            self.db.add_all([ExperimentEvidence(experiment_id=model.id, note_evidence_id=value) for value in item.evidence_ids])
            self.db.add_all([ExperimentContribution(experiment_id=model.id, contribution_id=contribution_map[value].id) for value in item.supports_contribution_client_ids])
        await self.db.flush()
        self.db.expire(profile, ["contributions", "experiments"])
        saved = await self._profile(note_id)
        assert saved is not None
        return self._response(saved)
    async def _profile(self, note_id: uuid.UUID):
        return await self.db.scalar(select(ResearchNoteProfile).where(ResearchNoteProfile.note_id == note_id).options(selectinload(ResearchNoteProfile.contributions).selectinload(ResearchContribution.evidence_links), selectinload(ResearchNoteProfile.experiments).selectinload(ResearchExperiment.evidence_links), selectinload(ResearchNoteProfile.experiments).selectinload(ResearchExperiment.contribution_links)))
    @staticmethod
    def _response(profile: ResearchNoteProfile) -> ResearchProfileResponse:
        return ResearchProfileResponse(id=profile.id,note_id=profile.note_id,background=profile.background,prior_work_limitations=profile.prior_work_limitations,research_problem=profile.research_problem,method_summary=profile.method_summary,results_summary=profile.results_summary,conclusion=profile.conclusion,limitations=profile.limitations,my_thoughts=profile.my_thoughts,created_at=profile.created_at,updated_at=profile.updated_at,
            contributions=[ContributionResponse(id=x.id,order_index=x.order_index,problem=x.problem,prior_limitation=x.prior_limitation,innovation=x.innovation,solution=x.solution,evidence_summary=x.evidence_summary,evidence_ids=[v.note_evidence_id for v in x.evidence_links]) for x in profile.contributions],
            experiments=[ExperimentResponse(id=x.id,order_index=x.order_index,task=x.task,datasets=x.datasets_json,baselines=x.baselines_json,metrics=x.metrics_json,result=x.result,conclusion=x.conclusion,evidence_ids=[v.note_evidence_id for v in x.evidence_links],contribution_ids=[v.contribution_id for v in x.contribution_links]) for x in profile.experiments])
