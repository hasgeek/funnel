"""migrate to urltype

Revision ID: 9aa60ff2a0ea
Revises: 38394aa411d0
Create Date: 2019-02-21 08:48:06.335465

"""

# revision identifiers, used by Alembic.
revision = '9aa60ff2a0ea'
down_revision = '38394aa411d0'

import sqlalchemy as sa  # NOQA
from alembic import op

from coaster.sqlalchemy import UrlType


def upgrade():
    op.alter_column('profile', 'logo_url', existing_type=sa.Unicode(2000), type_=UrlType())
    op.alter_column('project', 'website', existing_type=sa.Unicode(2000), type_=UrlType())
    op.alter_column('project', 'bg_image', existing_type=sa.Unicode(2000), type_=UrlType())
    op.alter_column('project', 'explore_url', existing_type=sa.Unicode(2000), type_=UrlType())
    op.alter_column('project', 'buy_tickets_url', existing_type=sa.Unicode(2000), type_=UrlType())
    op.alter_column('project', 'banner_video_url', existing_type=sa.Unicode(2000), type_=UrlType())
    op.alter_column('project', 'hasjob_embed_url', existing_type=sa.Unicode(2000), type_=UrlType())
    op.alter_column('proposal', 'slides', existing_type=sa.Unicode(2000), type_=UrlType())
    op.alter_column('proposal', 'preview_video', existing_type=sa.Unicode(2000), type_=UrlType())
    op.alter_column('session', 'banner_image_url', existing_type=sa.Unicode(2000), type_=UrlType())


def downgrade():
    op.alter_column('profile', 'logo_url', existing_type=UrlType(), type_=sa.Unicode(2000))
    op.alter_column('project', 'website', existing_type=UrlType(), type_=sa.Unicode(2000))
    op.alter_column('project', 'bg_image', existing_type=UrlType(), type_=sa.Unicode(2000))
    op.alter_column('project', 'explore_url', existing_type=UrlType(), type_=sa.Unicode(2000))
    op.alter_column('project', 'buy_tickets_url', existing_type=UrlType(), type_=sa.Unicode(2000))
    op.alter_column('project', 'banner_video_url', existing_type=UrlType(), type_=sa.Unicode(2000))
    op.alter_column('project', 'hasjob_embed_url', existing_type=UrlType(), type_=sa.Unicode(2000))
    op.alter_column('proposal', 'slides', existing_type=UrlType(), type_=sa.Unicode(2000))
    op.alter_column('proposal', 'preview_video', existing_type=UrlType(), type_=sa.Unicode(2000))
    op.alter_column('session', 'banner_image_url', existing_type=UrlType(), type_=sa.Unicode(2000))
