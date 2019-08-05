# -*- coding: utf-8 -*-

"""Label.name check constraint

Revision ID: 034863dbaac2
Revises: 111c9755ae39
Create Date: 2019-05-10 00:51:46.302304

"""

# revision identifiers, used by Alembic.
revision = '034863dbaac2'
down_revision = '111c9755ae39'

from alembic import op
import sqlalchemy as sa  # NOQA


def upgrade():
    op.create_check_constraint('label_name_check', 'label', "name <> ''")


def downgrade():
    op.drop_constraint('label_name_check', 'label')
