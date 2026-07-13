"""add low base high values to emission factors"""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("emission_factors")}
    for name in ("value_low", "value_base", "value_high"):
        if name not in columns:
            op.add_column("emission_factors", sa.Column(name, sa.Float(), nullable=True))
    op.execute("UPDATE emission_factors SET value_low = value, value_base = value, value_high = value")


def downgrade():
    for name in ("value_high", "value_base", "value_low"):
        op.drop_column("emission_factors", name)
