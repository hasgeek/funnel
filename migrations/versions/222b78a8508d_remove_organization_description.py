"""Remove organization.description.

Revision ID: 222b78a8508d
Revises: 6ebbe0cc8e19
Create Date: 2020-05-05 01:32:02.241787

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import column, table

from coaster.gfm import markdown

# revision identifiers, used by Alembic.
revision = '222b78a8508d'
down_revision = '6ebbe0cc8e19'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

organization_table = table(
    'organization',
    column('id', sa.Integer()),
    column('title', sa.Unicode()),
    column('description', sa.UnicodeText()),
)
profile_table = table(
    'profile',
    column('id', sa.Integer()),
    column('organization_id', sa.Integer()),
    column('description_text', sa.UnicodeText()),
    column('description_html', sa.UnicodeText()),
)


def upgrade() -> None:
    # Copy over data
    conn = op.get_bind()
    orgs = conn.execute(
        sa.select(
            organization_table.c.id,
            organization_table.c.title,
            organization_table.c.description,
        ).where(organization_table.c.description != '')
    )
    for org in orgs:
        blank_profile = conn.scalar(
            sa.select(sa.func.count(profile_table.c.id)).where(
                sa.and_(
                    profile_table.c.organization_id == org.id,
                    profile_table.c.description_text == '',
                )
            )
        )
        if blank_profile:
            print("Updating", org.title)  # noqa: T201
            op.execute(
                profile_table.update()
                .where(profile_table.c.organization_id == org.id)
                .values(
                    description_text=org.description,
                    description_html=markdown(org.description),
                )
            )
        else:
            print("Skipping", org.title)  # noqa: T201
    op.drop_column('organization', 'description')


def downgrade() -> None:
    op.add_column(
        'organization',
        sa.Column(
            'description',
            sa.TEXT(),
            autoincrement=False,
            nullable=False,
            server_default='',
        ),
    )
    op.alter_column('organization', 'description', server_default=None)
