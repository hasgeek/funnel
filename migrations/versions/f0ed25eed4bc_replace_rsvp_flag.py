"""Replace RSVP flag.

Revision ID: f0ed25eed4bc
Revises: 37b764bbddd8
Create Date: 2023-11-20 17:23:54.141389

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f0ed25eed4bc'
down_revision: str = '37b764bbddd8'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


project = sa.table(
    'project',
    sa.column('id', sa.Integer()),
    sa.column('rsvp_state', sa.SmallInteger()),
    sa.column('allow_rsvp', sa.Boolean()),
)


class RsvpState:
    NONE = 1
    ALL = 2


def upgrade(engine_name: str = '') -> None:
    """Upgrade all databases."""
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name: str = '') -> None:
    """Downgrade all databases."""
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    """Upgrade default database."""
    op.add_column('project', sa.Column('rsvp_state', sa.SmallInteger(), nullable=True))
    op.execute(
        project.update().values(
            rsvp_state=sa.case(
                (project.c.allow_rsvp.is_(False), RsvpState.NONE),
                (project.c.allow_rsvp.is_(True), RsvpState.ALL),
                else_=RsvpState.NONE,
            )
        )
    )
    op.alter_column('project', 'rsvp_state', nullable=False)
    op.drop_column('project', 'allow_rsvp')


def downgrade_() -> None:
    """Downgrade default database."""
    op.add_column(
        'project',
        sa.Column('allow_rsvp', sa.BOOLEAN(), nullable=True),
    )
    op.execute(
        project.update().values(
            rsvp_state=sa.case(
                (project.c.rsvp_state.is_(RsvpState.NONE), False),
                (project.c.rsvp_state.is_(RsvpState.ALL), True),
                else_=False,
            )
        )
    )
    op.alter_column('project', 'allow_rsvp', nullable=False)
    op.drop_column('project', 'rsvp_state')
