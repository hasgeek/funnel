"""Moderator report models.

Revision ID: 79719ee38228
Revises: 047ebdac558b
Create Date: 2020-06-09 15:42:27.791372

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '79719ee38228'
down_revision = '047ebdac558b'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        'comment_moderator_report',
        sa.Column('comment_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('report_type', sa.SmallInteger(), nullable=False),
        sa.Column('reported_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['comment_id'], ['comment.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_comment_moderator_report_comment_id'),
        'comment_moderator_report',
        ['comment_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_comment_moderator_report_user_id'),
        'comment_moderator_report',
        ['user_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_comment_moderator_report_user_id'),
        table_name='comment_moderator_report',
    )
    op.drop_index(
        op.f('ix_comment_moderator_report_comment_id'),
        table_name='comment_moderator_report',
    )
    op.drop_table('comment_moderator_report')
