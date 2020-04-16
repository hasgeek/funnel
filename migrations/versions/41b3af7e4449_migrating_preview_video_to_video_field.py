# -*- coding: utf-8 -*-
"""migrating preview_video to video field

Revision ID: 41b3af7e4449
Revises: d50c3d8e3f33
Create Date: 2020-04-15 10:36:15.558161

"""

from textwrap import dedent
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

    op.execute(
        sa.DDL(
            dedent(
                '''
        UPDATE proposal SET search_vector = setweight(to_tsvector('english', COALESCE(title, '')), 'A') || setweight(to_tsvector('english', COALESCE(abstract_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(outline_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(requirements_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(slides, '')), 'B') || setweight(to_tsvector('english', COALESCE(links, '')), 'B') || setweight(to_tsvector('english', COALESCE(bio_text, '')), 'B');

        DROP TRIGGER proposal_search_vector_trigger ON proposal;
        DROP FUNCTION proposal_search_vector_update();

        CREATE FUNCTION proposal_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.abstract_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.outline_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.requirements_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.slides, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.links, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.bio_text, '')), 'B');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER proposal_search_vector_trigger BEFORE INSERT OR UPDATE ON proposal
        FOR EACH ROW EXECUTE PROCEDURE proposal_search_vector_update();
                '''
            )
        )
    )

    op.drop_column('proposal', 'preview_video')


def downgrade():
    op.add_column(
        'proposal', sa.Column('preview_video', sa.UnicodeText(), nullable=True)
    )

    op.execute(
        sa.DDL(
            dedent(
                '''
        UPDATE proposal SET search_vector = setweight(to_tsvector('english', COALESCE(title, '')), 'A') || setweight(to_tsvector('english', COALESCE(abstract_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(outline_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(requirements_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(slides, '')), 'B') || setweight(to_tsvector('english', COALESCE(preview_video, '')), 'C') || setweight(to_tsvector('english', COALESCE(links, '')), 'B') || setweight(to_tsvector('english', COALESCE(bio_text, '')), 'B');

        DROP TRIGGER proposal_search_vector_trigger ON proposal;
        DROP FUNCTION proposal_search_vector_update();

        CREATE FUNCTION proposal_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.abstract_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.outline_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.requirements_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.slides, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.preview_video, '')), 'C') || setweight(to_tsvector('english', COALESCE(NEW.links, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.bio_text, '')), 'B');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER proposal_search_vector_trigger BEFORE INSERT OR UPDATE ON proposal
        FOR EACH ROW EXECUTE PROCEDURE proposal_search_vector_update();
                '''
            )
        )
    )
