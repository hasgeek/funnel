"""Move content into description.

Revision ID: f8204bcd438
Revises: 55b1ef63bee
Create Date: 2014-12-03 00:57:54.098592

"""

# revision identifiers, used by Alembic.
revision = 'f8204bcd438'
down_revision = '55b1ef63bee'

from alembic import op
from sqlalchemy.sql import column, table
import sqlalchemy as sa

from coaster.gfm import markdown
from coaster.sqlalchemy import JsonDict


def upgrade():
    connection = op.get_bind()
    proposal_space = table(
        'proposal_space',
        column('id', sa.INTEGER()),
        column('description_text', sa.TEXT()),
        column('description_html', sa.TEXT()),
        column('content', JsonDict()),
    )

    results = connection.execute(proposal_space.select())
    for space in results:
        if space['content']:
            for section, title in [
                ('format', "Format"),
                ('criteria', "Criteria for proposals"),
                ('panel', "Editorial panel"),
                ('dates', "Important dates"),
                ('open_source', "Commitment to Open Source"),
                ('themes', "Theme"),
            ]:
                modified = False
                text = space['description_text']
                if space['content'].get(section):
                    modified = True
                    text = (
                        text
                        + '\r\n\r\n'
                        + "## "
                        + title
                        + '\r\n\r\n'
                        + space['content'][section]
                    )
                if modified:
                    html = markdown(text)
                    connection.execute(
                        proposal_space.update()
                        .where(proposal_space.c.id == space['id'])
                        .values(
                            {
                                'description_text': text,
                                'description_html': html,
                                'content': {},
                            }
                        )
                    )


def downgrade():
    # XXX: There is no downgrade since we clobbered the content column's content. We're one-way.
    pass
