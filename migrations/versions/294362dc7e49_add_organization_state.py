"""Add organization state.

Revision ID: 294362dc7e49
Revises: 1c9cbf3a1e5e
Create Date: 2021-08-10 18:04:27.259907

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '294362dc7e49'
down_revision = '1c9cbf3a1e5e'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


class ORGANIZATION_STATE:  # noqa: N801
    """State codes for organizations."""

    #: Regular, active organization
    ACTIVE = 1
    #: Suspended organization (cause and explanation not included here)
    SUSPENDED = 2


def upgrade(engine_name: str = '') -> None:
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name: str = '') -> None:
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    op.add_column(
        'organization',
        sa.Column(
            'state',
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text(str(ORGANIZATION_STATE.ACTIVE)),
        ),
    )
    op.alter_column('organization', 'state', server_default=None)
    op.create_check_constraint(
        'organization_state_check', 'organization', 'state IN (1, 2)'
    )


def downgrade_() -> None:
    op.drop_constraint('organization_state_check', 'organization', type_='check')
    op.drop_column('organization', 'state')


def upgrade_geoname() -> None:
    pass


def downgrade_geoname() -> None:
    pass
