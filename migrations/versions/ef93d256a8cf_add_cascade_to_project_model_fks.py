"""add cascade to project model fks

Revision ID: ef93d256a8cf
Revises: 347c236041d3
Create Date: 2019-04-02 17:15:39.113950

"""

# revision identifiers, used by Alembic.
revision = 'ef93d256a8cf'
down_revision = '347c236041d3'

from alembic import op


def upgrade():
    op.drop_constraint('project_admin_team_id_fkey', 'project', type_='foreignkey')
    op.create_foreign_key('project_admin_team_id_fkey',
        'project', 'team', ['admin_team_id'], ['id'], ondelete='SET NULL')
    op.drop_constraint('project_review_team_id_fkey', 'project', type_='foreignkey')
    op.create_foreign_key('project_review_team_id_fkey',
        'project', 'team', ['review_team_id'], ['id'], ondelete='SET NULL')
    op.drop_constraint('project_checkin_team_id_fkey', 'project', type_='foreignkey')
    op.create_foreign_key('project_checkin_team_id_fkey',
        'project', 'team', ['checkin_team_id'], ['id'], ondelete='SET NULL')


def downgrade():
    op.drop_constraint('project_admin_team_id_fkey', 'project', type_='foreignkey')
    op.create_foreign_key('project_admin_team_id_fkey',
        'project', 'team', ['admin_team_id'], ['id'])
    op.drop_constraint('project_review_team_id_fkey', 'project', type_='foreignkey')
    op.create_foreign_key('project_review_team_id_fkey',
        'project', 'team', ['review_team_id'], ['id'])
    op.drop_constraint('project_checkin_team_id_fkey', 'project', type_='foreignkey')
    op.create_foreign_key('project_checkin_team_id_fkey',
        'project', 'team', ['checkin_team_id'], ['id'])
