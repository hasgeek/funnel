"""logo url banner url hasjob embed

Revision ID: f71e7bbf3d47
Revises: b553db89a76e
Create Date: 2018-11-19 12:56:31.717765

"""

revision = 'f71e7bbf3d47'
down_revision = 'b553db89a76e'

from alembic import op
import sqlalchemy as sa
from coaster.sqlalchemy import JsonDict


def upgrade():
    op.add_column('profile', sa.Column('logo_url', sa.Unicode(length=2000), nullable=True))
    op.add_column('project', sa.Column('banner_video_url', sa.Unicode(length=2000), nullable=True))
    op.add_column('project', sa.Column('boxoffice_data', JsonDict(), server_default='{}', nullable=True))
    op.add_column('project', sa.Column('hasjob_embed_url', sa.Unicode(length=2000), nullable=True))
    op.add_column('project', sa.Column('hasjob_embed_limit', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('project', 'hasjob_embed_limit')
    op.drop_column('project', 'hasjob_embed_url')
    op.drop_column('project', 'boxoffice_data')
    op.drop_column('project', 'banner_video_url')
    op.drop_column('profile', 'logo_url')
