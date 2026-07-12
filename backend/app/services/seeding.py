import json
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Batch, EvidenceArtifact, Project
from app.services.imports import import_csv_bytes


def seed_database(db: Session, seed_dir: str | None = None) -> dict:
    configured = seed_dir or os.getenv("SEED_DIR")
    if not configured:
        return {"seeded": False, "reason": "seed_directory_unavailable"}
    root = Path(configured)
    if not root.is_dir():
        return {"seeded": False, "reason": "seed_directory_unavailable"}
    project_data = json.loads((root / "demo_project.json").read_text(encoding="utf-8"))
    project = db.scalar(select(Project).where(Project.code == project_data["code"]))
    if not project:
        project = Project(
            **{key: project_data[key] for key in ("name", "code", "system_stage", "owner_organization")},
            description=project_data.get("description", project_data.get("boundary", "")),
        )
        db.add(project)
        db.flush()
    batch = db.scalar(select(Batch).where(Batch.batch_code == "SFE-BG-2023-11"))
    if not batch:
        batch = Batch(
            project_id=project.id,
            batch_code="SFE-BG-2023-11",
            started_at=datetime.fromisoformat("2023-11-08T00:00:00"),
            ended_at=datetime.fromisoformat("2023-11-24T00:00:00"),
            temperature_c=None,
            flow_m3_d=None,
            hrt_h=None,
            reactor_carrier="column",
            configuration="sulfur_iron",
            sulfur_iron_ratio=None,
            notes="六批第三方实验室送样检测背景数据",
            evidence_level="background",
        )
        db.add(batch)
        db.flush()
    imported = import_csv_bytes(db, batch.id, (root / "background_third_party_samples.csv").read_bytes(), idempotent=True)
    if not db.scalar(select(EvidenceArtifact.id).limit(1)):
        for record in json.loads((root / "background_evidence.json").read_text(encoding="utf-8")):
            db.add(
                EvidenceArtifact(
                    name=record["name"],
                    artifact_type="background_record",
                    rights_holder=None,
                    status=record["status"],
                    file_reference=record.get("ref"),
                    applicable_claims=[],
                    limitations=record.get("limitations", ""),
                    disclosure_level="summary_only",
                    sha256=None,
                )
            )
        db.commit()
    return {"seeded": True, "project_id": project.id, "batch_id": batch.id, **imported}
