# -*- coding: utf-8 -*-
"""data migrate checkin teams to membership

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
    'project',
    column('id', sa.Integer()),
    column('checkin_team_id', sa.Integer()),
    column('admin_team_id', sa.Integer()),
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
    column('revoked_by_id', sa.Integer()),
    column('granted_at', sa.TIMESTAMP(timezone=True)),
    column('record_type', sa.Integer()),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('updated_at', sa.TIMESTAMP(timezone=True)),
    column('revoked_at', sa.TIMESTAMP(timezone=True)),
)


def get_existing_membership(conn, user_id, project_id):
    return conn.execute(
        sa.select([project_crew_membership.c.id])
        .where(
            sa.and_(
                project_crew_membership.c.project_id == project_id,
                project_crew_membership.c.user_id == user_id,
                project_crew_membership.c.revoked_at == None,  # NOQA
            )
        )
        .returning(
            project_crew_membership.c.id,
            project_crew_membership.c.is_editor,
            project_crew_membership.c.is_concierge,
            project_crew_membership.c.is_usher,
        )
    ).first()


def upgrade():
    conn = op.get_bind()
    projects = conn.execute(
        sa.select([project.c.id, project.c.checkin_team_id, project.c.admin_team_id])
    )
    for project_id, checkin_team_id, admin_team_id in projects:
        # migrate checkin team
        checkin_team_users = conn.execute(
            sa.select([users_teams.c.user_id, users_teams.c.created_at]).where(
                users_teams.c.team_id == checkin_team_id
            )
        )
        checkin_dict = {
            user_id: created_at for user_id, created_at in checkin_team_users
        }
        admin_team_users = conn.execute(
            sa.select([users_teams.c.user_id, users_teams.c.created_at]).where(
                users_teams.c.team_id == admin_team_id
            )
        )
        admin_dict = {user_id: created_at for user_id, created_at in admin_team_users}
        all_users = set(checkin_dict.keys() + admin_dict.keys())

        for user_id in all_users:
            conn.execute(
                project_crew_membership.insert().values(
                    {
                        'id': uuid4(),
                        'project_id': project_id,
                        'user_id': user_id,
                        'is_editor': user_id in admin_dict,
                        'is_concierge': user_id in admin_dict,
                        'is_usher': user_id in checkin_dict,
                        'granted_by_id': None,
                        'granted_at': checkin_dict[user_id]
                        if user_id in checkin_dict
                        else admin_dict[user_id],
                        'record_type': MEMBERSHIP_RECORD_TYPE.DIRECT_ADD,
                        'created_at': sa.func.now(),
                        'updated_at': sa.func.now(),
                    }
                )
            )


def downgrade():
    conn = op.get_bind()
    conn.execute(project_crew_membership.delete())
