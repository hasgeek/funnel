"""Deprecate Session.speaker_bio.

Revision ID: 284c10efdbce
Revises: 2cc791c09075
Create Date: 2021-02-09 10:01:25.069803

"""

from textwrap import dedent
from typing import Optional, Tuple, Union

import progressbar.widgets
import sqlalchemy as sa
from alembic import op
from progressbar import ProgressBar
from sqlalchemy.sql import column, table

from coaster.utils import markdown

# revision identifiers, used by Alembic.
revision = '284c10efdbce'
down_revision = '2cc791c09075'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


session = table(
    'session',
    column('id', sa.Integer()),
    column('description_text', sa.UnicodeText()),
    column('description_html', sa.UnicodeText()),
    column('speaker_bio_text', sa.UnicodeText()),
)


def get_progressbar(label, maxval):
    return ProgressBar(
        maxval=maxval,
        widgets=[
            label,
            ': ',
            progressbar.widgets.Percentage(),
            ' ',
            progressbar.widgets.Bar(),
            ' ',
            progressbar.widgets.ETA(),
            ' ',
        ],
    )


def session_description(row):
    description = f"{row.description_text.strip()}\r\n"
    if row.speaker_bio_text:
        description += f"\r\n### Speaker bio\r\n\r\n{row.speaker_bio_text.strip()}\r\n"
    return description


def upgrade() -> None:
    conn = op.get_bind()

    count = conn.scalar(sa.select(sa.func.count('*')).select_from(session))
    progress = get_progressbar("Sessions", count)
    progress.start()
    items = conn.execute(session.select())
    for counter, item in enumerate(items):
        description_text = session_description(item)
        description_html = markdown(description_text)
        conn.execute(
            sa.update(session)
            .where(session.c.id == item.id)
            .values(
                description_text=description_text,
                description_html=description_html,
            )
        )
        progress.update(counter)
    progress.finish()

    op.execute(
        sa.DDL(
            dedent(
                '''
                UPDATE session SET search_vector = setweight(to_tsvector('english', COALESCE(title, '')), 'A') || setweight(to_tsvector('english', COALESCE(description_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(speaker, '')), 'A');

                DROP TRIGGER session_search_vector_trigger ON session;
                DROP FUNCTION session_search_vector_update();

                CREATE FUNCTION session_search_vector_update() RETURNS trigger AS $$
                BEGIN
                    NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.description_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.speaker, '')), 'A');
                    RETURN NEW;
                END
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER session_search_vector_trigger BEFORE INSERT OR UPDATE ON session
                FOR EACH ROW EXECUTE PROCEDURE session_search_vector_update();
                '''
            )
        )
    )

    op.drop_column('session', 'speaker_bio_text')
    op.drop_column('session', 'speaker_bio_html')


def downgrade() -> None:
    op.add_column(
        'session',
        sa.Column(
            'speaker_bio_html',
            sa.TEXT(),
            autoincrement=False,
            nullable=False,
            server_default='',
        ),
    )
    op.alter_column('session', 'speaker_bio_html', server_default=None)
    op.add_column(
        'session',
        sa.Column(
            'speaker_bio_text',
            sa.TEXT(),
            autoincrement=False,
            nullable=False,
            server_default='',
        ),
    )
    op.alter_column('session', 'speaker_bio_text', server_default=None)

    op.execute(
        sa.DDL(
            dedent(
                '''
                UPDATE session SET search_vector = setweight(to_tsvector('english', COALESCE(title, '')), 'A') || setweight(to_tsvector('english', COALESCE(description_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(speaker_bio_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(speaker, '')), 'A');

                DROP TRIGGER session_search_vector_trigger ON session;
                DROP FUNCTION session_search_vector_update();

                CREATE FUNCTION session_search_vector_update() RETURNS trigger AS $$
                BEGIN
                    NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.description_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.speaker_bio_text, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.speaker, '')), 'A');
                    RETURN NEW;
                END
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER session_search_vector_trigger BEFORE INSERT OR UPDATE ON session
                FOR EACH ROW EXECUTE PROCEDURE session_search_vector_update();
                '''
            )
        )
    )
