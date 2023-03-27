"""Use underscores in account names.

Revision ID: f346a7cc783a
Revises: d0a6fab28b7f
Create Date: 2023-03-27 22:16:42.701748

"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f346a7cc783a'
down_revision: str = 'd0a6fab28b7f'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


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
