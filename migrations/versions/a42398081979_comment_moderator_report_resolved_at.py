"""Comment moderator report resolved_at.

Revision ID: a42398081979
Revises: 2d2797b91909
Create Date: 2020-09-11 12:13:15.019538

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'a42398081979'
down_revision = '2d2797b91909'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        'comment_moderator_report',
        sa.Column('resolved_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        op.f('ix_comment_moderator_report_resolved_at'),
        'comment_moderator_report',
        ['resolved_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_comment_moderator_report_resolved_at'),
        table_name='comment_moderator_report',
    )
    op.drop_column('comment_moderator_report', 'resolved_at')
