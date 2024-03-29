"""URLs now use string instead of text.

Revision ID: 4f805eefa9f4
Revises: b8a87e6a24f1
Create Date: 2022-12-22 15:06:54.491988

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4f805eefa9f4'
down_revision: str = 'b8a87e6a24f1'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade(engine_name: str = '') -> None:
    """Upgrade all databases."""
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name: str = '') -> None:
    """Downgrade all databases."""
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    """Upgrade database bind ''."""
    with op.batch_alter_table('profile', schema=None) as batch_op:
        batch_op.alter_column(
            'website',
            existing_type=sa.UnicodeText(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'logo_url',
            existing_type=sa.UnicodeText(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'banner_image_url',
            existing_type=sa.UnicodeText(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )

    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.alter_column(
            'website',
            existing_type=sa.UnicodeText(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'bg_image',
            existing_type=sa.UnicodeText(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'buy_tickets_url',
            existing_type=sa.UnicodeText(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'banner_video_url',
            existing_type=sa.UnicodeText(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'hasjob_embed_url',
            existing_type=sa.UnicodeText(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )

    with op.batch_alter_table('session', schema=None) as batch_op:
        batch_op.alter_column(
            'banner_image_url',
            existing_type=sa.UnicodeText(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )

    with op.batch_alter_table('shortlink', schema=None) as batch_op:
        batch_op.alter_column(
            'url',
            existing_type=sa.UnicodeText(),
            type_=sa.Unicode(),
            existing_nullable=False,
        )


def downgrade_() -> None:
    """Downgrade database bind ''."""
    with op.batch_alter_table('shortlink', schema=None) as batch_op:
        batch_op.alter_column(
            'url',
            existing_type=sa.Unicode(),
            type_=sa.UnicodeText(),
            existing_nullable=False,
        )

    with op.batch_alter_table('session', schema=None) as batch_op:
        batch_op.alter_column(
            'banner_image_url',
            existing_type=sa.Unicode(),
            type_=sa.UnicodeText(),
            existing_nullable=True,
        )

    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.alter_column(
            'hasjob_embed_url',
            existing_type=sa.Unicode(),
            type_=sa.UnicodeText(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'banner_video_url',
            existing_type=sa.Unicode(),
            type_=sa.UnicodeText(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'buy_tickets_url',
            existing_type=sa.Unicode(),
            type_=sa.UnicodeText(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'bg_image',
            existing_type=sa.Unicode(),
            type_=sa.UnicodeText(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'website',
            existing_type=sa.Unicode(),
            type_=sa.UnicodeText(),
            existing_nullable=True,
        )

    with op.batch_alter_table('profile', schema=None) as batch_op:
        batch_op.alter_column(
            'banner_image_url',
            existing_type=sa.Unicode(),
            type_=sa.UnicodeText(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'logo_url',
            existing_type=sa.Unicode(),
            type_=sa.UnicodeText(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'website',
            existing_type=sa.Unicode(),
            type_=sa.UnicodeText(),
            existing_nullable=True,
        )


def upgrade_geoname() -> None:
    """Upgrade database bind 'geoname'."""


def downgrade_geoname() -> None:
    """Downgrade database bind 'geoname'."""
