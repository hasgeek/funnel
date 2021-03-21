"""Add commentset fields.

Revision ID: a23e88f06478
Revises: 284c10efdbce
Create Date: 2021-03-22 02:54:30.416806
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a23e88f06478'
down_revision = '284c10efdbce'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'commentset',
        sa.Column('last_comment_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        'commentset_membership',
        sa.Column(
            'is_muted',
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.false(),
        ),
    )
    op.alter_column('commentset_membership', 'is_muted', server_default=None)


def downgrade():
    op.drop_column('commentset_membership', 'is_muted')
    op.drop_column('commentset', 'last_comment_at')
