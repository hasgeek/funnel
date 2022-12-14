"""Migrating preview_video to video field.

Revision ID: 41b3af7e4449
Revises: 530c22761e27
Create Date: 2020-04-15 10:36:15.558161

"""

from textwrap import dedent
from typing import Optional, Tuple, Union
import csv
import re
import urllib.parse

from alembic import op
from sqlalchemy.sql import column, table
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '41b3af7e4449'
down_revision = '530c22761e27'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None

# --- Tables ---------------------------------------------------------------------------
proposal = table(
    'proposal',
    column('id', sa.Integer()),
    column('preview_video', sa.UnicodeText()),
    column('video_id', sa.UnicodeText()),
    column('video_source', sa.UnicodeText()),
)


# --- Functions ------------------------------------------------------------------------

troublesome_filename = 'preview-video-troublesome.csv'


def parse_video_url(video_url: str):
    video_source = 'raw'
    video_id = video_url

    parsed = urllib.parse.urlparse(video_url)
    if parsed.netloc is None:
        raise ValueError("Invalid video URL")

    if parsed.netloc in ['youtube.com', 'www.youtube.com', 'm.youtube.com']:
        if parsed.path == '/watch':
            queries = urllib.parse.parse_qs(parsed.query)
            if 'v' in queries and queries['v']:
                video_id = queries['v'][0]
                video_source = 'youtube'
            else:
                raise ValueError(
                    f"{video_url}: YouTube video URLs need to be in the format: "
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                )
        elif parsed.path.startswith('/embed/'):
            video_id = parsed.path[7:]
            if video_id:
                video_source = 'youtube'
            else:
                raise ValueError(
                    f"{video_url}: YouTube video URLs need to be in the format: "
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                )
        else:
            raise ValueError(
                f"{video_url}: YouTube video URLs need to be in the format: "
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            )
    elif parsed.netloc == 'youtu.be':
        video_id = parsed.path.lstrip('/')
        if video_id:
            video_source = 'youtube'
        else:
            raise ValueError(
                "YouTube short URLs need to be in the format: "
                "https://youtu.be/dQw4w9WgXcQ"
            )
    elif parsed.netloc in ['vimeo.com', 'www.vimeo.com']:
        video_id = parsed.path.lstrip('/')
        if video_id:
            video_source = 'vimeo'
        else:
            raise ValueError(
                "Vimeo video URLs need to be in the format: "
                "https://vimeo.com/336892869"
            )
    elif parsed.netloc == 'drive.google.com':
        if parsed.path.startswith('/open'):
            queries = urllib.parse.parse_qs(parsed.query)
            if 'id' in queries and queries['id']:
                video_id = queries['id'][0]
                video_source = 'googledrive'
            else:
                raise ValueError(
                    f"{video_url}: Google Drive video URLs need to be in the format: "
                    "https://drive.google.com/open?id=1rwHdWYnF4asdhsnDwLECoqZQy4o or "
                    "https://drive.google.com/file/d/1rwHdWYnF4asdhsnDwLECoqZQy4o/view"
                )
        elif parsed.path.startswith('/file/d/'):
            video_id = parsed.path[8:]
            if video_id.endswith('/view'):
                video_id = video_id[:-5]
            elif video_id.endswith('/preview'):
                video_id = video_id[:-8]
            video_source = 'googledrive'
        else:
            raise ValueError(
                f"{video_url}: Google Drive video URLs need to be in the format: "
                "https://drive.google.com/open?id=1rwHdWYnF4asdhsnDwLECoqZQy4o or "
                "https://drive.google.com/file/d/1rwHdWYnF4asdhsnDwLECoqZQy4o/view"
            )
    return video_source, video_id


def make_video_url(video_source: str, video_id: str):
    if video_source == 'youtube':
        return f'https://www.youtube.com/watch?v={video_id}'
    elif video_source == 'vimeo':
        return f'https://vimeo.com/{video_id}'
    elif video_source == 'googledrive':
        return f'https://drive.google.com/file/d/{video_id}/view'
    elif video_source == 'raw':
        return video_id
    raise ValueError("Unknown video source")


# --- Migrations -----------------------------------------------------------------------


def upgrade():
    conn = op.get_bind()

    proposals = conn.execute(
        proposal.select().where(proposal.c.preview_video.isnot(None))
    )
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

    conn = op.get_bind()
    proposals = conn.execute(proposal.select().where(proposal.c.video_id.isnot(None)))
    for prop in proposals:
        conn.execute(
            sa.update(proposal)
            .where(proposal.c.id == prop['id'])
            .values(
                preview_video=make_video_url(prop['video_source'], prop['video_id'])
            )
        )

    conn.execute(
        sa.update(proposal)
        .where(proposal.c.preview_video.isnot(None))
        .values(video_source=None, video_id=None)
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
