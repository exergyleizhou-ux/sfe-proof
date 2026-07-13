import csv
import io
import math
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Measurement, Sample

MAX_CSV_BYTES = 2 * 1024 * 1024
WIDE_COLUMNS = {
    "date",
    "NO2_N_in_mg_L",
    "NO2_N_out_mg_L",
    "TN_in_mg_L",
    "TN_out_mg_L",
    "NO3_N_in_mg_L",
    "NO3_N_out_mg_L",
}
LONG_COLUMNS = {"sample_code", "sample_role", "parameter_code", "value", "unit"}


def import_csv_bytes(db: Session, batch_id: int, content: bytes, *, idempotent: bool = False) -> dict:
    if len(content) > MAX_CSV_BYTES:
        raise ValueError("CSV超过2 MiB限制")
    try:
        rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    except UnicodeDecodeError as exc:
        raise ValueError("CSV必须使用UTF-8编码") from exc
    if not rows:
        raise ValueError("CSV没有数据行")
    columns = set(rows[0])
    if WIDE_COLUMNS.issubset(columns):
        return _import_wide(db, batch_id, rows, idempotent=idempotent)
    if LONG_COLUMNS.issubset(columns):
        return _import_long(db, batch_id, rows, idempotent=idempotent)
    expected = sorted(WIDE_COLUMNS if "date" in columns else LONG_COLUMNS)
    raise ValueError(f"CSV字段不受支持，需要: {expected}")


def _finite(raw: str, field: str) -> float:
    value = float(raw.removeprefix("<"))
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{field}必须为有限非负数")
    return value


def _sample(db: Session, batch_id: int, code: str, defaults: dict, idempotent: bool) -> tuple[Sample, bool]:
    existing = db.scalar(select(Sample).where(Sample.sample_code == code))
    if existing:
        if existing.batch_id != batch_id:
            raise ValueError(f"样本编号{code}已属于其他批次")
        if not idempotent:
            raise ValueError(f"样本编号{code}已存在")
        return existing, False
    sample = Sample(batch_id=batch_id, sample_code=code, **defaults)
    db.add(sample)
    db.flush()
    return sample, True


def _measurement(db: Session, sample: Sample, data: dict, idempotent: bool) -> bool:
    existing = db.scalar(
        select(Measurement).where(
            Measurement.sample_id == sample.id,
            Measurement.parameter_code == data["parameter_code"],
        )
    )
    if existing:
        if idempotent:
            return False
        raise ValueError(f"{sample.sample_code}的{data['parameter_code']}已存在")
    db.add(Measurement(sample_id=sample.id, **data))
    return True


def _result(rows: int, accepted: int, samples: int, measurements: int, errors: list[dict]) -> dict:
    return {
        "rows_received": rows,
        "accepted": accepted,
        "samples_created": samples,
        "measurements_created": measurements,
        "errors": errors,
    }


def _import_wide(db: Session, batch_id: int, rows: list[dict], *, idempotent: bool) -> dict:
    accepted = samples_created = measurements_created = 0
    errors: list[dict] = []
    for line, row in enumerate(rows, start=2):
        try:
            sampled_at = datetime.fromisoformat(row["date"])
            pending_samples = pending_measurements = 0
            with db.begin_nested():
                for role, suffix in (("influent", "in_mg_L"), ("effluent", "out_mg_L")):
                    sample, created = _sample(
                        db,
                        batch_id,
                        f"SFE-BG-{row['date']}-{role}",
                        {
                            "sample_role": role,
                            "provenance_type": row.get("provenance_type") or "submitted_to_third_party_lab",
                            "sampled_at": sampled_at,
                            "sampler_name": None if row.get("sampler") in (None, "", "未记录") else row["sampler"],
                            "sampler_organization": row.get("client"),
                            "sampling_location": row.get("sampling_location"),
                            "laboratory_name": row.get("laboratory"),
                            "laboratory_report_ref": row.get("laboratory_report_ref"),
                            "chain_of_custody_ref": row.get("chain_of_custody_ref"),
                            "verified_sampling": False,
                            "notes": "第三方实验室送样检测，不等于第三方现场采样",
                        },
                        idempotent,
                    )
                    pending_samples += int(created)
                    for prefix in ("TN", "NO3_N", "NO2_N"):
                        raw = row[f"{prefix}_{suffix}"]
                        value = _finite(raw, f"{prefix}_{suffix}")
                        pending_measurements += int(
                            _measurement(
                                db,
                                sample,
                                {
                                    "parameter_code": f"{prefix}_mg_L",
                                    "value": value,
                                    "unit": "mg/L",
                                    "qualifier": "less_than" if raw.startswith("<") else "equal",
                                    "detection_limit": value if raw.startswith("<") else None,
                                    "method": None,
                                    "measured_at": sampled_at,
                                    "data_grade": "reported",
                                },
                                idempotent,
                            )
                        )
            accepted += 1
            samples_created += pending_samples
            measurements_created += pending_measurements
        except (KeyError, TypeError, ValueError) as exc:
            errors.append({"row": line, "message": str(exc)})
    db.commit()
    return _result(len(rows), accepted, samples_created, measurements_created, errors)


def _import_long(db: Session, batch_id: int, rows: list[dict], *, idempotent: bool) -> dict:
    accepted = samples_created = measurements_created = 0
    errors: list[dict] = []
    for line, row in enumerate(rows, start=2):
        try:
            value = _finite(row["value"], "value")
            if not row["unit"].strip():
                raise ValueError("unit不能为空")
            measured_at = datetime.fromisoformat(row["measured_at"]) if row.get("measured_at") else None
            with db.begin_nested():
                sample, created = _sample(
                    db,
                    batch_id,
                    row["sample_code"].strip(),
                    {
                        "sample_role": row["sample_role"],
                        "provenance_type": row.get("provenance_type") or "team_p0_experiment",
                        "sampled_at": datetime.fromisoformat(row["sampled_at"]) if row.get("sampled_at") else measured_at,
                        "sampler_name": row.get("sampler_name"),
                        "sampler_organization": row.get("sampler_organization"),
                        "sampling_location": row.get("sampling_location"),
                        "laboratory_name": row.get("laboratory_name"),
                        "laboratory_report_ref": row.get("laboratory_report_ref"),
                        "chain_of_custody_ref": row.get("chain_of_custody_ref"),
                        "verified_sampling": row.get("verified_sampling", "false").lower() == "true",
                        "notes": row.get("notes") or "",
                    },
                    idempotent,
                )
                made_measurement = _measurement(
                    db,
                    sample,
                    {
                        "parameter_code": row["parameter_code"],
                        "value": value,
                        "unit": row["unit"].strip(),
                        "qualifier": row.get("qualifier") or "equal",
                        "detection_limit": float(row["detection_limit"]) if row.get("detection_limit") else None,
                        "method": row.get("method"),
                        "measured_at": measured_at,
                        "data_grade": row.get("data_grade") or "measured",
                    },
                    idempotent,
                )
            accepted += 1
            samples_created += int(created)
            measurements_created += int(made_measurement)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append({"row": line, "message": str(exc)})
    db.commit()
    return _result(len(rows), accepted, samples_created, measurements_created, errors)
