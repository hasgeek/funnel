"""Url field length.

Revision ID: 60a132ae73f1
Revises: d6b1904bea0e
Create Date: 2018-11-20 18:01:51.811819

"""

# revision identifiers, used by Alembic.
revision = '60a132ae73f1'
down_revision = 'd6b1904bea0e'

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.alter_column(
        'project',
        'bg_image',
        existing_type=sa.Unicode(length=250),
        type_=sa.Unicode(length=2000),
        existing_nullable=True,
    )
    op.alter_column(
        'project',
        'website',
        existing_type=sa.Unicode(length=250),
        type_=sa.Unicode(length=2000),
        existing_nullable=True,
    )
    op.alter_column(
        'project',
        'buy_tickets_url',
        existing_type=sa.Unicode(length=250),
        type_=sa.Unicode(length=2000),
        existing_nullable=True,
    )
    op.alter_column(
        'project',
        'explore_url',
        existing_type=sa.Unicode(length=250),
        type_=sa.Unicode(length=2000),
        existing_nullable=True,
    )
    op.alter_column(
        'proposal',
        'preview_video',
        existing_type=sa.Unicode(length=250),
        type_=sa.Unicode(length=2000),
        existing_nullable=True,
    )
    op.alter_column(
        'proposal',
        'slides',
        existing_type=sa.Unicode(length=250),
        type_=sa.Unicode(length=2000),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'proposal',
        'slides',
        existing_type=sa.Unicode(length=2000),
        type_=sa.Unicode(length=250),
        existing_nullable=True,
    )
    op.alter_column(
        'proposal',
        'preview_video',
        existing_type=sa.Unicode(length=2000),
        type_=sa.Unicode(length=250),
        existing_nullable=True,
    )
    op.alter_column(
        'project',
        'explore_url',
        existing_type=sa.Unicode(length=2000),
        type_=sa.Unicode(length=250),
        existing_nullable=True,
    )
    op.alter_column(
        'project',
        'buy_tickets_url',
        existing_type=sa.Unicode(length=2000),
        type_=sa.Unicode(length=250),
        existing_nullable=True,
    )
    op.alter_column(
        'project',
        'website',
        existing_type=sa.Unicode(length=2000),
        type_=sa.Unicode(length=250),
        existing_nullable=True,
    )
    op.alter_column(
        'project',
        'bg_image',
        existing_type=sa.Unicode(length=2000),
        type_=sa.Unicode(length=250),
        existing_nullable=True,
    )
