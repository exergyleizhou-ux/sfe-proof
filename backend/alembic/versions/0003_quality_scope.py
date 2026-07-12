"""scope quality findings by project batch and scan"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("quality_findings")}
    added_project = "project_id" not in columns
    added_batch = "batch_id" not in columns
    definitions = {
        "project_id": sa.Column("project_id", sa.Integer(), nullable=True),
        "batch_id": sa.Column("batch_id", sa.Integer(), nullable=True),
        "scan_run_id": sa.Column("scan_run_id", sa.String(length=36), nullable=True),
        "created_at": sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    }
    for name, definition in definitions.items():
        if name not in columns:
            op.add_column("quality_findings", definition)
    if added_project:
        op.create_foreign_key("fk_quality_project", "quality_findings", "projects", ["project_id"], ["id"])
    if added_batch:
        op.create_foreign_key("fk_quality_batch", "quality_findings", "batches", ["batch_id"], ["id"])
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("quality_findings")}
    for name, column in (
        ("ix_quality_findings_project_id", "project_id"),
        ("ix_quality_findings_batch_id", "batch_id"),
        ("ix_quality_findings_scan_run_id", "scan_run_id"),
    ):
        if name not in indexes:
            op.create_index(name, "quality_findings", [column])


def downgrade():
    op.drop_index("ix_quality_findings_scan_run_id", table_name="quality_findings")
    op.drop_index("ix_quality_findings_batch_id", table_name="quality_findings")
    op.drop_index("ix_quality_findings_project_id", table_name="quality_findings")
    op.drop_constraint("fk_quality_batch", "quality_findings", type_="foreignkey")
    op.drop_constraint("fk_quality_project", "quality_findings", type_="foreignkey")
    for name in ("created_at", "scan_run_id", "batch_id", "project_id"):
        op.drop_column("quality_findings", name)
