"""Moderator report model

Revision ID: 954f066e0e4b
Revises: 047ebdac558b
Create Date: 2020-05-22 00:33:39.113290

"""

from alembic import op
from sqlalchemy_utils import UUIDType
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '954f066e0e4b'
down_revision = '047ebdac558b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'comment_moderator_report',
        sa.Column('reported_by_id', sa.Integer(), nullable=False),
        sa.Column('comment_id', sa.Integer(), nullable=False),
        sa.Column('report_type', sa.SmallInteger(), nullable=False),
        sa.Column('uuid', UUIDType(binary=False), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['comment_id'], ['comment.id'],),
        sa.ForeignKeyConstraint(['reported_by_id'], ['user.id'],),
        sa.PrimaryKeyConstraint('reported_by_id', 'comment_id'),
        sa.UniqueConstraint('uuid'),
    )


def downgrade():
    op.drop_table('comment_moderator_report')
