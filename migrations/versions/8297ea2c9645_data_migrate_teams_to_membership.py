# -*- coding: utf-8 -*-
"""data migrate teams to membership

Revision ID: 8297ea2c9645
Revises: 8cb98498a659
Create Date: 2019-10-23 19:42:48.165500

"""

# revision identifiers, used by Alembic.
revision = '8297ea2c9645'
down_revision = '8cb98498a659'

from uuid import uuid4

from alembic import op
from sqlalchemy.sql import column, table
from sqlalchemy_utils import UUIDType
import sqlalchemy as sa  # NOQA

from funnel.models.membership import MEMBERSHIP_RECORD_TYPE

project = table(
    'project', column('id', sa.Integer()), column('checkin_team_id', sa.Integer())
)

users_teams = table(
    'users_teams',
    column('user_id', sa.Integer()),
    column('team_id', sa.Integer()),
    column('created_at', sa.TIMESTAMP(timezone=True)),
)

project_crew_membership = table(
    'project_crew_membership',
    column('id', UUIDType(binary=False)),
    column('project_id', sa.Integer()),
    column('user_id', sa.Integer()),
    column('is_editor', sa.Boolean()),
    column('is_concierge', sa.Boolean()),
    column('is_usher', sa.Boolean()),
    column('granted_by_id', sa.Integer()),
    column('granted_at', sa.TIMESTAMP(timezone=True)),
    column('record_type', sa.Integer()),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('updated_at', sa.TIMESTAMP(timezone=True)),
)


def upgrade():
    conn = op.get_bind()
    projects = conn.execute(sa.select([project.c.id, project.c.checkin_team_id]))
    for project_id, checkin_team_id in projects:
        checkin_team_users = conn.execute(
            sa.select([users_teams.c.user_id, users_teams.c.created_at]).where(
                users_teams.c.team_id == checkin_team_id
            )
        )
        for user_id, created_at in checkin_team_users:
            existing_membership = conn.execute(
                sa.select([project_crew_membership.c.id]).where(
                    sa.and_(
                        project_crew_membership.c.project_id == project_id,
                        project_crew_membership.c.user_id == user_id,
                    )
                )
            ).first()
            if existing_membership is None:
                conn.execute(
                    project_crew_membership.insert()
                    .values(
                        {
                            'id': uuid4(),
                            'project_id': project_id,
                            'user_id': user_id,
                            'is_editor': False,
                            'is_concierge': False,
                            'is_usher': True,
                            'granted_by_id': None,
                            'granted_at': created_at,
                            'record_type': MEMBERSHIP_RECORD_TYPE.DIRECT_ADD,
                            'created_at': sa.func.now(),
                            'updated_at': sa.func.now(),
                        }
                    )
                    .returning(project_crew_membership.c.id)
                )


def downgrade():
    conn = op.get_bind()
    projects = conn.execute(sa.select([project.c.id, project.c.checkin_team_id]))
    for project_id, checkin_team_id in projects:
        checkin_team_users = conn.execute(
            sa.select([users_teams.c.user_id, users_teams.c.created_at]).where(
                users_teams.c.team_id == checkin_team_id
            )
        )
        for user_id, created_at in checkin_team_users:
            conn.execute(
                project_crew_membership.delete().where(
                    sa.and_(
                        project_crew_membership.c.project_id == project_id,
                        project_crew_membership.c.user_id == user_id,
                        project_crew_membership.c.is_editor == False,
                        project_crew_membership.c.is_concierge == False,
                        project_crew_membership.c.is_usher == True,
                        project_crew_membership.c.granted_by_id == None,  # NOQA
                    )
                )
            )
