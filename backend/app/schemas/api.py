from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectIn(BaseModel):
    name: str
    code: str
    description: str = ""
    system_stage: str = "competition_prototype"
    owner_organization: str = ""


class ProjectOut(ProjectIn, ORMModel):
    id: int
    created_at: datetime


class BatchIn(BaseModel):
    project_id: int
    batch_code: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    temperature_c: float | None = None
    flow_m3_d: float | None = None
    hrt_h: float | None = None
    reactor_carrier: str = "column"
    configuration: str = "sulfur_iron"
    sulfur_iron_ratio: str | None = None
    notes: str = ""
    evidence_level: str = "student_p0"


class BatchOut(BatchIn, ORMModel):
    id: int


class SampleIn(BaseModel):
    sample_code: str
    sample_role: str
    provenance_type: str
    sampled_at: datetime | None = None
    sampler_name: str | None = None
    sampler_organization: str | None = None
    sampling_location: str | None = None
    laboratory_name: str | None = None
    laboratory_report_ref: str | None = None
    chain_of_custody_ref: str | None = None
    verified_sampling: bool = False
    notes: str = ""


class SampleOut(SampleIn, ORMModel):
    id: int
    batch_id: int
    provenance_warning: str | None = None


class MeasurementIn(BaseModel):
    parameter_code: str
    value: float
    unit: str
    qualifier: str = "equal"
    detection_limit: float | None = None
    method: str | None = None
    measured_at: datetime | None = None
    data_grade: str = "measured"

    @model_validator(mode="after")
    def validate_detection_limit(self):
        if self.qualifier == "less_than" and self.detection_limit is None:
            raise ValueError("less_than requires detection_limit")
        return self


class ConcentrationRequest(BaseModel):
    influent: list[float]
    effluent: list[float]
    effluent_qualifiers: list[str] | None = None


class LoadRequest(BaseModel):
    influent_mg_l: float
    effluent_mg_l: float
    flow_m3_d: float | None = None


class MassBalanceRequest(BaseModel):
    inputs: dict[str, float]
    outputs: dict[str, float]
    required_terms: list[str]
    tolerance_pct: float = 5


class MRVActivity(BaseModel):
    scenario: Literal["baseline", "project"]
    name: str
    factor_activity: str
    amount_low: float
    amount_base: float
    amount_high: float
    unit: str
    source: str
    data_grade: Literal["measured", "reported", "estimated", "placeholder"]
    placeholder: bool = False

    @model_validator(mode="after")
    def finite_nonnegative(self):
        import math

        values = (self.amount_low, self.amount_base, self.amount_high)
        if not all(math.isfinite(value) and value >= 0 for value in values):
            raise ValueError("MRV活动量必须为有限非负数")
        if not self.amount_low <= self.amount_base <= self.amount_high:
            raise ValueError("活动量必须满足low <= base <= high")
        return self


class MRVRequest(BaseModel):
    functional_unit: Literal["1_m3_treated", "1_kg_TN_removed"] = "1_m3_treated"
    activities: list[MRVActivity]
    factor_set_version: str = "demo-cn-screening-2026.1"
    n2o_addressed: bool = False
    equal_effluent_goal_confirmed: bool = False


class ClaimRequest(BaseModel):
    text: str


class QualityScanRequest(BaseModel):
    batch_id: int


class CertificateRequest(BaseModel):
    input_snapshot: dict[str, Any]
    result_snapshot: dict[str, Any]
    factor_set_version: str = "demo-cn-screening-2026.1"
    git_commit_sha: str = "uncommitted"


class CertificateManifest(BaseModel):
    certificate_id: str
    canonical_input: str
    canonical_result: str
    input_hash: str
    result_hash: str
    algorithm_version: str
    git_commit_sha: str
    factor_set_version: str

    @model_validator(mode="after")
    def limit_payload(self):
        if len(self.canonical_input.encode()) + len(self.canonical_result.encode()) > 2 * 1024 * 1024:
            raise ValueError("manifest规范JSON超过2 MiB限制")
        return self


class VerifyRequest(BaseModel):
    manifest: CertificateManifest | None = None
    input_snapshot: dict[str, Any] | None = None
    result_snapshot: dict[str, Any] | None = None


class EvidenceIn(BaseModel):
    name: str
    artifact_type: str
    rights_holder: str | None = None
    status: str
    file_reference: str | None = None
    applicable_claims: list[str] = Field(default_factory=list)
    limitations: str = ""
    disclosure_level: str = "summary_only"
    sha256: str | None = None
