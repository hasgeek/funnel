"""project location

Revision ID: 9a0d8fa7da29
Revises: eec2fad0f3e9
Create Date: 2018-11-28 10:48:57.245376

"""

revision = '9a0d8fa7da29'
down_revision = 'eec2fad0f3e9'

from alembic import op
import sqlalchemy as sa  # NOQA
from coaster.sqlalchemy import JsonDict


def upgrade():
    op.create_table('project_location',
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('geonameid', sa.Integer(), nullable=False),
        sa.Column('primary', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.PrimaryKeyConstraint('project_id', 'geonameid')
    )
    op.create_index(op.f('ix_project_location_geonameid'), 'project_location', ['geonameid'], unique=False)
    op.add_column(u'project', sa.Column('location', sa.Unicode(length=50), nullable=True))
    op.add_column(u'project', sa.Column('parsed_location', JsonDict(), server_default='{}', nullable=False))


def downgrade():
    op.drop_column(u'project', 'parsed_location')
    op.drop_column(u'project', 'location')
    op.drop_index(op.f('ix_project_location_geonameid'), table_name='project_location')
    op.drop_table('project_location')
