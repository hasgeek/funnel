# -*- coding: utf-8 -*-

"""add_badge_template_to_event

Revision ID: 90cc904ece17
Revises: cf775ffe502e
Create Date: 2018-04-17 14:35:52.263777

"""

# revision identifiers, used by Alembic.
revision = '90cc904ece17'
down_revision = 'cf775ffe502e'

from alembic import op
import sqlalchemy as sa  # NOQA


def upgrade():
    op.add_column(
        'event', sa.Column('badge_template', sa.Unicode(length=250), nullable=True)
    )


def downgrade():
    op.drop_column('event', 'badge_template')
