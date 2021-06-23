"""Fix membership granted_by.

Revision ID: d0097ec29880
Revises: bd465803af3a
Create Date: 2021-04-22 05:20:50.774828

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd0097ec29880'
down_revision = 'bd465803af3a'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'commentset_membership',
        'granted_by_id',
        existing_type=sa.INTEGER(),
        nullable=False,
    )
    op.alter_column(
        'proposal_membership',
        'granted_by_id',
        existing_type=sa.INTEGER(),
        nullable=False,
    )
    op.alter_column(
        'site_membership', 'granted_by_id', existing_type=sa.INTEGER(), nullable=False
    )


def downgrade():
    op.alter_column(
        'site_membership', 'granted_by_id', existing_type=sa.INTEGER(), nullable=True
    )
    op.alter_column(
        'proposal_membership',
        'granted_by_id',
        existing_type=sa.INTEGER(),
        nullable=True,
    )
    op.alter_column(
        'commentset_membership',
        'granted_by_id',
        existing_type=sa.INTEGER(),
        nullable=True,
    )
