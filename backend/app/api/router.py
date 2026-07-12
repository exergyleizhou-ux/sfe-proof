from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import ALGORITHM_VERSION
from app.db.session import get_db
from app.models.entities import Batch, EmissionFactor, EvidenceArtifact, EvidenceCertificate, Measurement, MRVRun, Project, QualityFinding, Sample
from app.schemas.api import (
    BatchIn,
    BatchOut,
    CertificateRequest,
    ClaimRequest,
    ConcentrationRequest,
    EvidenceIn,
    LoadRequest,
    MassBalanceRequest,
    MeasurementIn,
    MRVRequest,
    ProjectIn,
    ProjectOut,
    QualityScanRequest,
    SampleIn,
    VerifyRequest,
)
from app.services.calculations import concentration_reduction, load_reduction, mass_balance
from app.services.certificates import build_manifest, certificate_id, sha256, verify_submitted_manifest
from app.services.claims import check_claim
from app.services.export import export_html, export_json
from app.services.imports import MAX_CSV_BYTES, import_csv_bytes
from app.services.mrv import calculate_mrv
from app.services.provenance import warning_for
from app.services.quality import scan_samples

router = APIRouter(prefix="/api/v1")


def one(db: Session, model, item_id: int):
    item = db.get(model, item_id)
    if not item:
        raise HTTPException(404, "对象不存在")
    return item


def _batch_reductions(item: Batch) -> dict:
    result = {}
    for parameter in ("TN_mg_L", "NO3_N_mg_L", "NO2_N_mg_L"):
        influent = [m.value for sample in item.samples if sample.sample_role == "influent" for m in sample.measurements if m.parameter_code == parameter]
        effluent = [m.value for sample in item.samples if sample.sample_role == "effluent" for m in sample.measurements if m.parameter_code == parameter]
        qualifiers = [m.qualifier for sample in item.samples if sample.sample_role == "effluent" for m in sample.measurements if m.parameter_code == parameter]
        if influent and len(influent) == len(effluent):
            result[parameter] = concentration_reduction(influent, effluent, qualifiers)
    return result


@router.get("/projects", response_model=list[ProjectOut])
def projects(db: Session = Depends(get_db)):
    return list(db.scalars(select(Project).order_by(Project.id)))


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectIn, db: Session = Depends(get_db)):
    item = Project(**body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/projects/{item_id}", response_model=ProjectOut)
def get_project(item_id: int, db: Session = Depends(get_db)):
    return one(db, Project, item_id)


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    projects_list = list(db.scalars(select(Project)))
    batches_list = list(db.scalars(select(Batch)))
    samples_list = list(db.scalars(select(Sample)))
    return {
        "project_count": len(projects_list),
        "batch_count": len(batches_list),
        "sample_count": len(samples_list),
        "measurement_count": len(list(db.scalars(select(Measurement)))),
        "provenance_gap_count": sum(
            1 for sample in samples_list if sample.provenance_type == "submitted_to_third_party_lab" and (not sample.sampler_name or not sample.sampling_location)
        ),
        "latest_mrv": get_mrv(db.scalar(select(MRVRun.id).order_by(MRVRun.id.desc())), db) if db.scalar(select(MRVRun.id).limit(1)) else None,
    }


@router.get("/batches")
def batches(db: Session = Depends(get_db)):
    return [
        {
            "id": item.id,
            "project_id": item.project_id,
            "batch_code": item.batch_code,
            "started_at": item.started_at,
            "ended_at": item.ended_at,
            "flow_m3_d": item.flow_m3_d,
            "evidence_level": item.evidence_level,
            "notes": item.notes,
            "sample_count": len(item.samples),
        }
        for item in db.scalars(select(Batch).order_by(Batch.id))
    ]


@router.post("/batches", response_model=BatchOut, status_code=201)
def create_batch(body: BatchIn, db: Session = Depends(get_db)):
    one(db, Project, body.project_id)
    item = Batch(**body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/batches/{item_id}")
def get_batch(item_id: int, db: Session = Depends(get_db)):
    item = one(db, Batch, item_id)
    return {
        "id": item.id,
        "batch_code": item.batch_code,
        "project_id": item.project_id,
        "started_at": item.started_at,
        "ended_at": item.ended_at,
        "flow_m3_d": item.flow_m3_d,
        "notes": item.notes,
        "evidence_level": item.evidence_level,
        "calculations": _batch_reductions(item),
        "samples": [
            {
                "id": s.id,
                "sample_code": s.sample_code,
                "sample_role": s.sample_role,
                "sampled_at": s.sampled_at,
                "provenance_type": s.provenance_type,
                "sampler_name": s.sampler_name,
                "sampling_location": s.sampling_location,
                "laboratory_name": s.laboratory_name,
                "provenance_warning": warning_for(s.provenance_type),
                "measurements": [
                    {
                        "id": m.id,
                        "parameter_code": m.parameter_code,
                        "value": m.value,
                        "unit": m.unit,
                        "qualifier": m.qualifier,
                        "detection_limit": m.detection_limit,
                        "data_grade": m.data_grade,
                    }
                    for m in s.measurements
                ],
            }
            for s in item.samples
        ],
    }


@router.post("/batches/{item_id}/samples", status_code=201)
def create_sample(item_id: int, body: SampleIn, db: Session = Depends(get_db)):
    one(db, Batch, item_id)
    item = Sample(batch_id=item_id, **body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {**body.model_dump(mode="json"), "id": item.id, "batch_id": item.batch_id, "provenance_warning": warning_for(item.provenance_type)}


@router.post("/batches/{item_id}/import")
async def import_csv(item_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    one(db, Batch, item_id)
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(415, "只接受.csv文件")
    try:
        content = await file.read(MAX_CSV_BYTES + 1)
        return import_csv_bytes(db, item_id, content)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc


@router.get("/samples/{item_id}")
def get_sample(item_id: int, db: Session = Depends(get_db)):
    item = one(db, Sample, item_id)
    return {
        "id": item.id,
        "sample_code": item.sample_code,
        "provenance_type": item.provenance_type,
        "provenance_warning": warning_for(item.provenance_type),
        "measurements": [
            {"id": m.id, "parameter_code": m.parameter_code, "value": m.value, "unit": m.unit, "qualifier": m.qualifier, "detection_limit": m.detection_limit}
            for m in item.measurements
        ],
    }


@router.post("/samples/{item_id}/measurements", status_code=201)
def add_measurement(item_id: int, body: MeasurementIn, db: Session = Depends(get_db)):
    one(db, Sample, item_id)
    item = Measurement(sample_id=item_id, **body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, **body.model_dump(mode="json")}


@router.post("/calculations/concentration-reduction")
def calc_concentration(body: ConcentrationRequest):
    try:
        return concentration_reduction(body.influent, body.effluent, body.effluent_qualifiers)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/calculations/load-reduction")
def calc_load(body: LoadRequest):
    try:
        return load_reduction(body.influent_mg_l, body.effluent_mg_l, body.flow_m3_d)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/calculations/mass-balance")
def calc_balance(body: MassBalanceRequest):
    return mass_balance(body.inputs, body.outputs, body.required_terms, body.tolerance_pct)


@router.post("/quality/scan")
def quality_scan(body: QualityScanRequest, db: Session = Depends(get_db)):
    batch = one(db, Batch, body.batch_id)
    samples = [
        {
            "sample_code": sample.sample_code,
            "sample_role": sample.sample_role,
            "provenance_type": sample.provenance_type,
            "sampler_name": sample.sampler_name,
            "sampling_location": sample.sampling_location,
        }
        for sample in batch.samples
    ]
    measurements = [
        {
            "parameter_code": measurement.parameter_code,
            "value": measurement.value,
            "unit": measurement.unit,
            "qualifier": measurement.qualifier,
            "detection_limit": measurement.detection_limit,
        }
        for sample in batch.samples
        for measurement in sample.measurements
    ]
    results = scan_samples(samples, measurements)
    scan_run_id = str(uuid4())
    for row in results:
        db.add(QualityFinding(project_id=batch.project_id, batch_id=batch.id, scan_run_id=scan_run_id, **row))
    db.commit()
    return {
        "project_id": batch.project_id,
        "batch_id": batch.id,
        "scan_run_id": scan_run_id,
        "findings": [{**row, "project_id": batch.project_id, "batch_id": batch.id, "scan_run_id": scan_run_id} for row in results],
        "count": len(results),
    }


@router.get("/quality/findings")
def findings(batch_id: int = Query(...), scan_run_id: str | None = None, db: Session = Depends(get_db)):
    statement = select(QualityFinding).where(QualityFinding.batch_id == batch_id)
    if scan_run_id:
        statement = statement.where(QualityFinding.scan_run_id == scan_run_id)
    return [{column.name: getattr(item, column.name) for column in QualityFinding.__table__.columns} for item in db.scalars(statement.order_by(QualityFinding.id))]


@router.post("/mrv/runs", status_code=201)
def mrv_run(body: MRVRequest, db: Session = Depends(get_db)):
    registered = list(db.scalars(select(EmissionFactor).where(EmissionFactor.version == body.factor_set_version)))
    factors = {
        factor.applicable_activity: {
            "value_low": factor.value_low if factor.value_low is not None else factor.value,
            "value_base": factor.value_base if factor.value_base is not None else factor.value,
            "value_high": factor.value_high if factor.value_high is not None else factor.value,
            "source": factor.source,
            "unit": factor.unit,
            "placeholder": factor.is_placeholder,
        }
        for factor in registered
    }
    result = calculate_mrv(
        [activity.model_dump() for activity in body.activities],
        factors,
        body.factor_set_version,
        body.functional_unit,
        body.n2o_addressed,
        body.equal_effluent_goal_confirmed,
    )
    persisted = {key: value for key, value in result.items() if key != "confirmed_reduction_allowed"}
    unit_intensity = "gCO2e/kg TN" if body.functional_unit == "1_kg_TN_removed" else "gCO2e/m3"
    item = MRVRun(functional_unit=body.functional_unit, unit_intensity=unit_intensity, **persisted)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, **result, "functional_unit": body.functional_unit, "unit_intensity": unit_intensity}


@router.get("/mrv/factors")
def emission_factors(version: str = Query(...), db: Session = Depends(get_db)):
    return [
        {
            "name": factor.name,
            "activity": factor.applicable_activity,
            "value_low": factor.value_low,
            "value_base": factor.value_base,
            "value_high": factor.value_high,
            "unit": factor.unit,
            "source": factor.source,
            "version": factor.version,
            "data_grade": factor.data_grade,
            "placeholder": factor.is_placeholder,
        }
        for factor in db.scalars(select(EmissionFactor).where(EmissionFactor.version == version))
    ]


@router.get("/mrv/runs")
def list_mrv(db: Session = Depends(get_db)):
    return [{column.name: getattr(item, column.name) for column in MRVRun.__table__.columns} for item in db.scalars(select(MRVRun).order_by(MRVRun.id.desc()))]


@router.get("/mrv/runs/{item_id}")
def get_mrv(item_id: int, db: Session = Depends(get_db)):
    item = one(db, MRVRun, item_id)
    return {column.name: getattr(item, column.name) for column in MRVRun.__table__.columns}


@router.post("/mrv/runs/{item_id}/sensitivity")
def sensitivity(item_id: int, db: Session = Depends(get_db)):
    return one(db, MRVRun, item_id).sensitivity


@router.post("/claims/check")
def claims(body: ClaimRequest):
    return check_claim(body.text)


@router.post("/certificates", status_code=201)
def create_certificate(body: CertificateRequest, db: Session = Depends(get_db)):
    input_hash, result_hash = sha256(body.input_snapshot), sha256(body.result_snapshot)
    cid = certificate_id(input_hash)
    while db.scalar(select(EvidenceCertificate.id).where(EvidenceCertificate.certificate_id == cid)):
        cid = f"{certificate_id(input_hash)}-{uuid4().hex[:6].upper()}"
    item = EvidenceCertificate(
        certificate_id=cid,
        input_snapshot=body.input_snapshot,
        result_snapshot=body.result_snapshot,
        input_hash=input_hash,
        result_hash=result_hash,
        algorithm_version=ALGORITHM_VERSION,
        git_commit_sha=body.git_commit_sha,
        factor_set_version=body.factor_set_version,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _certificate_payload(item)


@router.get("/certificates/{cid}")
def get_certificate(cid: str, db: Session = Depends(get_db)):
    item = db.scalar(select(EvidenceCertificate).where(EvidenceCertificate.certificate_id == cid))
    if not item:
        raise HTTPException(404, "证书不存在")
    return _certificate_payload(item)


@router.get("/certificates/{cid}/manifest")
def download_certificate_manifest(cid: str, db: Session = Depends(get_db)):
    item = db.scalar(select(EvidenceCertificate).where(EvidenceCertificate.certificate_id == cid))
    if not item:
        raise HTTPException(404, "证书不存在")
    manifest = _certificate_manifest(item)
    return Response(
        export_json(manifest),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="certificate-manifest.json"'},
    )


@router.post("/certificates/{cid}/verify")
def verify_certificate(cid: str, body: VerifyRequest, db: Session = Depends(get_db)):
    item = db.scalar(select(EvidenceCertificate).where(EvidenceCertificate.certificate_id == cid))
    if not item:
        raise HTTPException(404, "证书不存在")
    if body.manifest is None and body.input_snapshot is None and body.result_snapshot is None:
        return {"certificate_id": cid, "status": "needs_payload", "valid": False, "input_hash_match": False, "result_hash_match": False}
    if body.manifest is None:
        if body.input_snapshot is None or body.result_snapshot is None:
            return {"certificate_id": cid, "status": "needs_payload", "valid": False, "input_hash_match": False, "result_hash_match": False}
        manifest = _certificate_manifest(item)
    else:
        manifest = body.manifest.model_dump()
    expected = _certificate_manifest(item)
    return {
        "certificate_id": cid,
        **verify_submitted_manifest(manifest, expected, body.input_snapshot, body.result_snapshot),
    }


def _certificate_manifest(item: EvidenceCertificate) -> dict:
    return build_manifest(
        item.certificate_id,
        item.input_snapshot,
        item.result_snapshot,
        item.algorithm_version,
        item.git_commit_sha,
        item.factor_set_version,
    )


def _certificate_payload(item: EvidenceCertificate) -> dict:
    return {
        "certificate_id": item.certificate_id,
        "input_hash": item.input_hash,
        "result_hash": item.result_hash,
        "algorithm_version": item.algorithm_version,
        "git_commit_sha": item.git_commit_sha,
        "factor_set_version": item.factor_set_version,
        "created_at": item.created_at,
        "status": item.status,
        "manifest": _certificate_manifest(item),
        "boundary": "证明计算来源和文件完整性；不证明采样真实性、算法科学结论正确，也不等于第三方核证或碳信用。",
    }


@router.get("/evidence")
def evidence(db: Session = Depends(get_db)):
    return [{column.name: getattr(item, column.name) for column in EvidenceArtifact.__table__.columns} for item in db.scalars(select(EvidenceArtifact))]


@router.post("/evidence", status_code=201)
def create_evidence(body: EvidenceIn, db: Session = Depends(get_db)):
    item = EvidenceArtifact(**body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, **body.model_dump()}


@router.get("/exports/batches/{item_id}")
def export_batch(item_id: int, format: str = Query("json", pattern="^(json|html)$"), db: Session = Depends(get_db)):
    payload = get_batch(item_id, db)
    return HTMLResponse(export_html("SFe批次导出", payload)) if format == "html" else Response(export_json(payload), media_type="application/json")


@router.get("/exports/mrv/{item_id}")
def export_mrv(item_id: int, format: str = Query("json", pattern="^(json|html)$"), db: Session = Depends(get_db)):
    payload = get_mrv(item_id, db)
    return HTMLResponse(export_html("SFe MRV导出", payload)) if format == "html" else Response(export_json(payload), media_type="application/json")
