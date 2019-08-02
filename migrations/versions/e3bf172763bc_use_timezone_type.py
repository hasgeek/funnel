# -*- coding: utf-8 -*-

"""Use timezone type

Revision ID: e3bf172763bc
Revises: 94ce3a9b7a3a
Create Date: 2019-02-20 16:25:30.611549

"""

# revision identifiers, used by Alembic.
revision = 'e3bf172763bc'
down_revision = '94ce3a9b7a3a'

from alembic import op
from sqlalchemy_utils import TimezoneType
import sqlalchemy as sa  # NOQA


def upgrade():
    op.alter_column(
        'project',
        'timezone',
        existing_type=sa.Unicode(40),
        type_=TimezoneType(backend='pytz'),
    )


def downgrade():
    op.alter_column(
        'project',
        'timezone',
        existing_type=TimezoneType(backend='pytz'),
        type_=sa.Unicode(40),
    )
