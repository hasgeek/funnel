"""Add video mixin to proposal and session.

Revision ID: 664141d5ec56
Revises: 20c10335b553
Create Date: 2020-03-16 16:06:28.827051

"""

revision = '664141d5ec56'
down_revision = '20c10335b553'

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column('proposal', sa.Column('video_id', sa.UnicodeText(), nullable=True))
    op.add_column(
        'proposal', sa.Column('video_source', sa.UnicodeText(), nullable=True)
    )
    op.add_column('session', sa.Column('video_id', sa.UnicodeText(), nullable=True))
    op.add_column('session', sa.Column('video_source', sa.UnicodeText(), nullable=True))


def downgrade() -> None:
    op.drop_column('session', 'video_source')
    op.drop_column('session', 'video_id')
    op.drop_column('proposal', 'video_source')
    op.drop_column('proposal', 'video_id')
