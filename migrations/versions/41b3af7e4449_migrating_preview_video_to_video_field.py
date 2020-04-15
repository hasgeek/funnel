# -*- coding: utf-8 -*-
"""migrating preview_video to video field

Revision ID: 41b3af7e4449
Revises: d50c3d8e3f33
Create Date: 2020-04-15 10:36:15.558161

"""

import csv
import re

from alembic import op
from sqlalchemy.sql import column, table
import sqlalchemy as sa

from funnel.models.video import parse_video_url

# revision identifiers, used by Alembic.
revision = '41b3af7e4449'
down_revision = 'd50c3d8e3f33'
branch_labels = None
depends_on = None


proposal = table(
    'proposal',
    column('id', sa.Integer()),
    column('preview_video', sa.UnicodeText()),
    column('video_id', sa.UnicodeText()),
    column('video_source', sa.UnicodeText()),
)


troublesome_filename = 'preview-video-troublesone.csv'


def upgrade():
    conn = op.get_bind()

    proposals = conn.execute(
        proposal.select().where(proposal.c.preview_video != None)
    )  # NOQA
    troublesome_previews = []
    for prop in proposals:
        if prop['preview_video'].strip():
            urls = re.findall(r'(https?:\/\/[^\ ]+)', prop['preview_video'])
            if urls:
                if len(urls) > 1:
                    troublesome_previews.append(
                        {
                            'proposal_id': prop['id'],
                            'preview_video': prop['preview_video'],
                        }
                    )
                try:
                    video_source, video_id = parse_video_url(urls[0])
                    conn.execute(
                        sa.update(proposal)
                        .where(proposal.c.id == prop['id'])
                        .values(video_source=video_source, video_id=video_id)
                    )
                except ValueError:
                    troublesome_previews.append(
                        {
                            'proposal_id': prop['id'],
                            'preview_video': prop['preview_video'],
                        }
                    )

    with open(troublesome_filename, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['proposal_id', 'preview_video'])
        writer.writeheader()
        writer.writerows(troublesome_previews)


def downgrade():
    conn = op.get_bind()

    proposals = conn.execute(proposal.select())
    for prop in proposals:
        if prop['preview_video']:
            conn.execute(
                sa.update(proposal)
                .where(proposal.c.id == prop['id'])
                .values(video_source=None, video_id=None)
            )
