"""Logo url banner url hasjob embed.

Revision ID: 70ffbc1bcf88
Revises: b553db89a76e
Create Date: 2018-11-19 16:19:47.976268

"""

revision = '70ffbc1bcf88'
down_revision = 'b553db89a76e'

import sqlalchemy as sa
from alembic import op

from coaster.sqlalchemy import JsonDict


def upgrade() -> None:
    op.add_column(
        'profile', sa.Column('logo_url', sa.Unicode(length=2000), nullable=True)
    )
    op.add_column(
        'project', sa.Column('banner_video_url', sa.Unicode(length=2000), nullable=True)
    )
    op.add_column(
        'project',
        sa.Column('boxoffice_data', JsonDict(), server_default='{}', nullable=False),
    )
    op.add_column(
        'project', sa.Column('hasjob_embed_limit', sa.Integer(), nullable=True)
    )
    op.add_column(
        'project', sa.Column('hasjob_embed_url', sa.Unicode(length=2000), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('project', 'hasjob_embed_url')
    op.drop_column('project', 'hasjob_embed_limit')
    op.drop_column('project', 'boxoffice_data')
    op.drop_column('project', 'banner_video_url')
    op.drop_column('profile', 'logo_url')
