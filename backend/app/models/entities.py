from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    code: Mapped[str] = mapped_column(String(64), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    system_stage: Mapped[str] = mapped_column(default="competition_prototype")
    owner_organization: Mapped[str] = mapped_column(default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    batches: Mapped[list[Batch]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Batch(Base):
    __tablename__ = "batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    batch_code: Mapped[str] = mapped_column(String(64), unique=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    temperature_c: Mapped[float | None]
    flow_m3_d: Mapped[float | None]
    hrt_h: Mapped[float | None]
    reactor_carrier: Mapped[str] = mapped_column(default="column")
    configuration: Mapped[str] = mapped_column(default="sulfur_iron")
    sulfur_iron_ratio: Mapped[str | None]
    notes: Mapped[str] = mapped_column(Text, default="")
    evidence_level: Mapped[str] = mapped_column(default="background")
    project: Mapped[Project] = relationship(back_populates="batches")
    samples: Mapped[list[Sample]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class Sample(Base):
    __tablename__ = "samples"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"))
    sample_code: Mapped[str] = mapped_column(String(96), unique=True)
    sample_role: Mapped[str]
    provenance_type: Mapped[str]
    sampled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sampler_name: Mapped[str | None]
    sampler_organization: Mapped[str | None]
    sampling_location: Mapped[str | None]
    laboratory_name: Mapped[str | None]
    laboratory_report_ref: Mapped[str | None]
    chain_of_custody_ref: Mapped[str | None]
    verified_sampling: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    batch: Mapped[Batch] = relationship(back_populates="samples")
    measurements: Mapped[list[Measurement]] = relationship(back_populates="sample", cascade="all, delete-orphan")


class Measurement(Base):
    __tablename__ = "measurements"
    __table_args__ = (UniqueConstraint("sample_id", "parameter_code", "measured_at", name="uq_measurement"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    sample_id: Mapped[int] = mapped_column(ForeignKey("samples.id"))
    parameter_code: Mapped[str]
    value: Mapped[float]
    unit: Mapped[str]
    qualifier: Mapped[str] = mapped_column(default="equal")
    detection_limit: Mapped[float | None]
    method: Mapped[str | None]
    measured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    data_grade: Mapped[str] = mapped_column(default="measured")
    sample: Mapped[Sample] = relationship(back_populates="measurements")


class HydraulicObservation(Base):
    __tablename__ = "hydraulic_observations"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"))
    flow_m3_d: Mapped[float | None]
    head_loss_m: Mapped[float | None]
    permeability: Mapped[float | None]
    before_backwash: Mapped[float | None]
    after_backwash: Mapped[float | None]
    backwash_duration_min: Mapped[float | None]
    recovery_time_min: Mapped[float | None]


class MaterialActivity(Base):
    __tablename__ = "material_activities"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"))
    material_name: Mapped[str]
    amount: Mapped[float]
    unit: Mapped[str]
    source: Mapped[str | None]
    source_batch: Mapped[str | None]
    data_grade: Mapped[str] = mapped_column(default="reported")


class EnergyActivity(Base):
    __tablename__ = "energy_activities"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"))
    equipment_name: Mapped[str]
    power_kw: Mapped[float | None]
    electricity_kwh: Mapped[float | None]
    runtime_h: Mapped[float | None]
    purpose: Mapped[str]
    data_grade: Mapped[str] = mapped_column(default="reported")


class EmissionFactor(Base):
    __tablename__ = "emission_factors"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    applicable_activity: Mapped[str]
    value: Mapped[float]
    value_low: Mapped[float | None]
    value_base: Mapped[float | None]
    value_high: Mapped[float | None]
    unit: Mapped[str]
    region: Mapped[str | None]
    year: Mapped[int | None]
    source: Mapped[str]
    version: Mapped[str]
    gwp_version: Mapped[str]
    data_grade: Mapped[str]
    is_placeholder: Mapped[bool] = mapped_column(Boolean, default=False)


class EvidenceArtifact(Base):
    __tablename__ = "evidence_artifacts"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    artifact_type: Mapped[str]
    rights_holder: Mapped[str | None]
    status: Mapped[str]
    file_reference: Mapped[str | None]
    applicable_claims: Mapped[list] = mapped_column(JSON, default=list)
    limitations: Mapped[str] = mapped_column(Text, default="")
    disclosure_level: Mapped[str] = mapped_column(default="summary_only")
    sha256: Mapped[str | None]


class QualityFinding(Base):
    __tablename__ = "quality_findings"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), index=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id"), index=True)
    scan_run_id: Mapped[str | None] = mapped_column(String(36), index=True)
    rule_id: Mapped[str]
    severity: Mapped[str]
    object_ref: Mapped[str]
    description: Mapped[str]
    innocent_explanation: Mapped[str]
    suggested_action: Mapped[str]
    status: Mapped[str] = mapped_column(default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MRVRun(Base):
    __tablename__ = "mrv_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    functional_unit: Mapped[str]
    input_snapshot_hash: Mapped[str]
    factor_set_version: Mapped[str]
    baseline_emissions: Mapped[float]
    project_emissions: Mapped[float]
    difference: Mapped[float]
    unit_intensity: Mapped[str] = mapped_column(default="gCO2e/m3")
    sensitivity: Mapped[dict] = mapped_column(JSON)
    contributors: Mapped[list] = mapped_column(JSON)
    missing_items: Mapped[list] = mapped_column(JSON)
    conclusion_status: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EvidenceCertificate(Base):
    __tablename__ = "evidence_certificates"
    id: Mapped[int] = mapped_column(primary_key=True)
    certificate_id: Mapped[str] = mapped_column(unique=True)
    input_snapshot: Mapped[dict] = mapped_column(JSON)
    result_snapshot: Mapped[dict] = mapped_column(JSON)
    input_hash: Mapped[str]
    result_hash: Mapped[str]
    algorithm_version: Mapped[str]
    git_commit_sha: Mapped[str]
    factor_set_version: Mapped[str]
    status: Mapped[str] = mapped_column(default="valid")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ClaimCheck(Base):
    __tablename__ = "claim_checks"
    id: Mapped[int] = mapped_column(primary_key=True)
    original_text: Mapped[str] = mapped_column(Text)
    matched_rules: Mapped[list] = mapped_column(JSON, default=list)
    result: Mapped[str]
    suggested_rewrite: Mapped[str] = mapped_column(Text)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
