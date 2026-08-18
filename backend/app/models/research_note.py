import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ResearchNoteProfile(Base):
    __tablename__ = "research_note_profiles"
    __table_args__ = (
        UniqueConstraint("note_id", name="research_note_profiles_note_id_key"),
        Index("ix_research_note_profiles_note_id", "note_id", unique=True),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    note_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"))
    background: Mapped[str] = mapped_column(Text, default="", server_default="")
    prior_work_limitations: Mapped[str] = mapped_column(Text, default="", server_default="")
    research_problem: Mapped[str] = mapped_column(Text, default="", server_default="")
    method_summary: Mapped[str] = mapped_column(Text, default="", server_default="")
    results_summary: Mapped[str] = mapped_column(Text, default="", server_default="")
    conclusion: Mapped[str] = mapped_column(Text, default="", server_default="")
    limitations: Mapped[str] = mapped_column(Text, default="", server_default="")
    future_work: Mapped[str] = mapped_column(Text, default="", server_default="")
    my_thoughts: Mapped[str] = mapped_column(Text, default="", server_default="")
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    note: Mapped["Note"] = relationship("Note", back_populates="research_profile")
    contributions: Mapped[list["ResearchContribution"]] = relationship("ResearchContribution", back_populates="profile", cascade="all, delete-orphan", order_by="ResearchContribution.order_index", lazy="selectin")
    experiments: Mapped[list["ResearchExperiment"]] = relationship("ResearchExperiment", back_populates="profile", cascade="all, delete-orphan", order_by="ResearchExperiment.order_index", lazy="selectin")


class ResearchContribution(Base):
    __tablename__ = "research_contributions"
    __table_args__ = (UniqueConstraint("research_note_id", "order_index", name="uq_research_contribution_order"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    research_note_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("research_note_profiles.id", ondelete="CASCADE"), index=True)
    order_index: Mapped[int] = mapped_column(Integer)
    problem: Mapped[str] = mapped_column(Text, default="", server_default="")
    prior_limitation: Mapped[str] = mapped_column(Text, default="", server_default="")
    innovation: Mapped[str] = mapped_column(Text, default="", server_default="")
    solution: Mapped[str] = mapped_column(Text, default="", server_default="")
    evidence_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile: Mapped[ResearchNoteProfile] = relationship("ResearchNoteProfile", back_populates="contributions")
    evidence_links: Mapped[list["ContributionEvidence"]] = relationship("ContributionEvidence", cascade="all, delete-orphan", lazy="selectin")


class ResearchExperiment(Base):
    __tablename__ = "research_experiments"
    __table_args__ = (UniqueConstraint("research_note_id", "order_index", name="uq_research_experiment_order"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    research_note_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("research_note_profiles.id", ondelete="CASCADE"), index=True)
    order_index: Mapped[int] = mapped_column(Integer)
    task: Mapped[str] = mapped_column(Text, default="", server_default="")
    datasets_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    baselines_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    metrics_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    result: Mapped[str] = mapped_column(Text, default="", server_default="")
    conclusion: Mapped[str] = mapped_column(Text, default="", server_default="")
    profile: Mapped[ResearchNoteProfile] = relationship("ResearchNoteProfile", back_populates="experiments")
    evidence_links: Mapped[list["ExperimentEvidence"]] = relationship("ExperimentEvidence", cascade="all, delete-orphan", lazy="selectin")
    contribution_links: Mapped[list["ExperimentContribution"]] = relationship("ExperimentContribution", cascade="all, delete-orphan", lazy="selectin")


class ContributionEvidence(Base):
    __tablename__ = "contribution_evidence"
    contribution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("research_contributions.id", ondelete="CASCADE"), primary_key=True)
    note_evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("note_evidence.id", ondelete="CASCADE"), primary_key=True)


class ExperimentEvidence(Base):
    __tablename__ = "experiment_evidence"
    experiment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("research_experiments.id", ondelete="CASCADE"), primary_key=True)
    note_evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("note_evidence.id", ondelete="CASCADE"), primary_key=True)


class ExperimentContribution(Base):
    __tablename__ = "experiment_contributions"
    experiment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("research_experiments.id", ondelete="CASCADE"), primary_key=True)
    contribution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("research_contributions.id", ondelete="CASCADE"), primary_key=True)
