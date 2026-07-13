"""correct persisted MRV emission unit labels"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE mrv_runs SET unit_intensity = 'kgCO2e/m3' WHERE unit_intensity = 'gCO2e/m3'")
    op.execute("UPDATE mrv_runs SET unit_intensity = 'kgCO2e/kg TN' WHERE unit_intensity = 'gCO2e/kg TN'")


def downgrade():
    op.execute("UPDATE mrv_runs SET unit_intensity = 'gCO2e/m3' WHERE unit_intensity = 'kgCO2e/m3'")
    op.execute("UPDATE mrv_runs SET unit_intensity = 'gCO2e/kg TN' WHERE unit_intensity = 'kgCO2e/kg TN'")
