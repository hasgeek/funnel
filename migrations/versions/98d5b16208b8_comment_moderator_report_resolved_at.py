"""comment moderator report resolved_at

Revision ID: 98d5b16208b8
Revises: 74e1fbb4a948
Create Date: 2020-09-08 18:59:42.910399

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '98d5b16208b8'
down_revision = '2d2797b91909'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'comment_moderator_report',
        sa.Column('resolved_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column('comment_moderator_report', 'resolved_at')
