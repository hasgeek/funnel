"""moderator report models

Revision ID: d5c65787f7d7
Revises: 047ebdac558b
Create Date: 2020-06-08 15:30:35.546176

"""

from alembic import op
from sqlalchemy_utils import UUIDType
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd5c65787f7d7'
down_revision = '047ebdac558b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'comment_moderator_report',
        sa.Column('reported_by_id', sa.Integer(), nullable=False),
        sa.Column('comment_id', sa.Integer(), nullable=False),
        sa.Column('report_type', sa.SmallInteger(), nullable=False),
        sa.Column('id', UUIDType(binary=False), nullable=False),
        sa.ForeignKeyConstraint(['comment_id'], ['comment.id'],),
        sa.ForeignKeyConstraint(['reported_by_id'], ['user.id'],),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_comment_moderator_report_comment_id'),
        'comment_moderator_report',
        ['comment_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_comment_moderator_report_reported_by_id'),
        'comment_moderator_report',
        ['reported_by_id'],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f('ix_comment_moderator_report_reported_by_id'),
        table_name='comment_moderator_report',
    )
    op.drop_index(
        op.f('ix_comment_moderator_report_comment_id'),
        table_name='comment_moderator_report',
    )
    op.drop_table('comment_moderator_report')
