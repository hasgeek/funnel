"""Use underscores in account names.

Revision ID: f346a7cc783a
Revises: 1d5e1a11661a
Create Date: 2023-03-27 22:16:42.701748

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f346a7cc783a'
down_revision: str = '1d5e1a11661a'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


profile = sa.table(
    'profile',
    sa.column('name', sa.Unicode),
)


def upgrade(engine_name='') -> None:
    """Upgrade all databases."""
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name='') -> None:
    """Downgrade all databases."""
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    """Upgrade database bind ''."""
    # Rename all profile names to use underscore instead of hyphen. Since there may be
    # existing (really old) accounts using underscores from before names were
    # validated, we have to first check for dupes and move them out of the way.
    # Unfortunately this process is not reversible.
    op.execute(
        profile.update()
        .values(name=sa.func.concat(profile.c.name, '_'))  # pylint: disable=E1102
        .where(
            profile.c.name.in_(
                sa.select(sa.func.replace(profile.c.name, '_', '-')).where(
                    profile.c.name.like(r'%\_%')
                )
            )
        )
    )
    # Now replace all hyphens with underscores
    op.execute(
        profile.update()
        .values(name=sa.func.replace(profile.c.name, '-', '_'))
        .where(profile.c.name.like('%-%'))
    )


def downgrade_() -> None:
    """Downgrade database bind ''."""
    # Rename from underscores back to hypens
    op.execute(
        profile.update()
        .values(name=sa.func.replace(profile.c.name, '_', '-'))
        .where(profile.c.name.like(r'%\_%'))
    )


def upgrade_geoname() -> None:
    """Upgrade database bind 'geoname'."""


def downgrade_geoname() -> None:
    """Downgrade database bind 'geoname'."""
