"""scope quality findings by project batch and scan"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("quality_findings", sa.Column("project_id", sa.Integer(), nullable=True))
    op.add_column("quality_findings", sa.Column("batch_id", sa.Integer(), nullable=True))
    op.add_column("quality_findings", sa.Column("scan_run_id", sa.String(length=36), nullable=True))
    op.add_column("quality_findings", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_foreign_key("fk_quality_project", "quality_findings", "projects", ["project_id"], ["id"])
    op.create_foreign_key("fk_quality_batch", "quality_findings", "batches", ["batch_id"], ["id"])
    op.create_index("ix_quality_findings_project_id", "quality_findings", ["project_id"])
    op.create_index("ix_quality_findings_batch_id", "quality_findings", ["batch_id"])
    op.create_index("ix_quality_findings_scan_run_id", "quality_findings", ["scan_run_id"])


def downgrade():
    op.drop_index("ix_quality_findings_scan_run_id", table_name="quality_findings")
    op.drop_index("ix_quality_findings_batch_id", table_name="quality_findings")
    op.drop_index("ix_quality_findings_project_id", table_name="quality_findings")
    op.drop_constraint("fk_quality_batch", "quality_findings", type_="foreignkey")
    op.drop_constraint("fk_quality_project", "quality_findings", type_="foreignkey")
    for name in ("created_at", "scan_run_id", "batch_id", "project_id"):
        op.drop_column("quality_findings", name)
