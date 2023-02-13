"""Simplify Proposal fields.

Revision ID: ad5013552ec6
Revises: daeb6753652a
Create Date: 2020-12-08 13:58:56.331436

"""

from textwrap import dedent
from typing import Optional, Tuple, Union

from alembic import op
from sqlalchemy.sql import column, table
import sqlalchemy as sa

from progressbar import ProgressBar
import progressbar.widgets

from coaster.utils import markdown

# revision identifiers, used by Alembic.
revision = 'ad5013552ec6'
down_revision = 'daeb6753652a'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


proposal = table(
    'proposal',
    column('id', sa.Integer()),
    # New fields
    column('body_text', sa.UnicodeText()),
    column('body_html', sa.UnicodeText()),
    column('description', sa.Unicode()),
    # Old fields
    column('abstract_text', sa.UnicodeText()),
    column('outline_text', sa.UnicodeText()),
    column('requirements_text', sa.UnicodeText()),
    column('slides', sa.Unicode()),
    column('links', sa.UnicodeText()),
    column('bio_text', sa.UnicodeText()),
    column('bio_html', sa.UnicodeText()),
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


def proposal_body(row):
    """Return text for proposal body."""
    # This template does not have localization because it adapts data from when the
    # website was English-only. CRLF line endings are used as per the HTTP form spec
    body = ''
    if row.abstract_text:
        body += f"{row.abstract_text.strip()}\r\n\r\n"
    if row.outline_text:
        body += f"### Outline\r\n\r\n{row.outline_text.strip()}\r\n\r\n"
    if row.requirements_text:
        body += f"### Requirements\r\n\r\n{row.requirements_text.strip()}\r\n\r\n"
    if row.bio_text:
        body += f"### Speaker bio\r\n\r\n{row.bio_text.strip()}\r\n\r\n"
    if row.links:
        links = '\r\n'.join(
            f" * {link}" for link in row.links.strip().splitlines() if link
        ).strip()
        body += f"### Links\r\n\r\n{links}\r\n\r\n"
    if row.slides:
        body += f"### Slides\r\n\r\n{row.slides.strip()}\r\n\r\n"
    return body


def upgrade():
    conn = op.get_bind()
    # Add and populate body and description fields
    op.add_column('proposal', sa.Column('body_text', sa.UnicodeText(), nullable=True))
    op.add_column('proposal', sa.Column('body_html', sa.UnicodeText(), nullable=True))
    op.add_column('proposal', sa.Column('description', sa.Unicode(), nullable=True))

    count = conn.scalar(sa.select(sa.func.count('*')).select_from(proposal))
    progress = get_progressbar("Proposals", count)
    progress.start()
    items = conn.execute(proposal.select())
    for counter, item in enumerate(items):
        body_text = proposal_body(item)
        body_html = markdown(body_text)
        conn.execute(
            sa.update(proposal)
            .where(proposal.c.id == item.id)
            .values(
                description=(
                    item.abstract_text.strip().splitlines()[0].strip()
                    if item.abstract_text
                    else ''
                ),
                body_text=body_text,
                body_html=body_html,
            )
        )
        progress.update(counter)
    progress.finish()

    op.alter_column('proposal', 'body_text', nullable=False)
    op.alter_column('proposal', 'body_html', nullable=False)
    op.alter_column('proposal', 'description', nullable=False)

    # Add and populate flag fields
    op.add_column(
        'proposal',
        sa.Column(
            'custom_description',
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.true(),
        ),
    )
    op.alter_column('proposal', 'custom_description', server_default=None)
    op.add_column(
        'proposal',
        sa.Column(
            'template',
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.false(),
        ),
    )
    op.alter_column('proposal', 'template', server_default=None)
    op.add_column(
        'proposal',
        sa.Column(
            'featured',
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.false(),
        ),
    )
    op.alter_column('proposal', 'featured', server_default=None)

    # Drop never-used coordinates columns
    op.drop_column('proposal', 'latitude')
    op.drop_column('proposal', 'longitude')

    # Update search vector
    op.execute(
        sa.DDL(
            dedent(
                '''
        UPDATE proposal SET search_vector = setweight(to_tsvector('english', COALESCE(title, '')), 'A') || setweight(to_tsvector('english', COALESCE(description, '')), 'B') || setweight(to_tsvector('english', COALESCE(body_text, '')), 'B');

        DROP TRIGGER proposal_search_vector_trigger ON proposal;
        DROP FUNCTION proposal_search_vector_update();

        CREATE FUNCTION proposal_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') || setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') || setweight(to_tsvector('english', COALESCE(NEW.body_text, '')), 'B');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER proposal_search_vector_trigger BEFORE INSERT OR UPDATE ON proposal
        FOR EACH ROW EXECUTE PROCEDURE proposal_search_vector_update();
                '''
            )
        )
    )


def downgrade():
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

    op.add_column(
        'proposal',
        sa.Column('longitude', sa.NUMERIC(), autoincrement=False, nullable=True),
    )
    op.add_column(
        'proposal',
        sa.Column('latitude', sa.NUMERIC(), autoincrement=False, nullable=True),
    )
    op.drop_column('proposal', 'featured')
    op.drop_column('proposal', 'template')
    op.drop_column('proposal', 'custom_description')
    op.drop_column('proposal', 'description')
    op.drop_column('proposal', 'body_html')
    op.drop_column('proposal', 'body_text')
