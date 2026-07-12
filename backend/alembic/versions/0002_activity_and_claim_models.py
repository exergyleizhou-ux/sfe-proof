"""add hydraulic activity factor and claim tables"""

from alembic import op

from app.db.session import Base
from app.models import entities  # noqa: F401

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.create_all(op.get_bind())


def downgrade():
    for table in ["claim_checks", "emission_factors", "energy_activities", "material_activities", "hydraulic_observations"]:
        op.drop_table(table)
