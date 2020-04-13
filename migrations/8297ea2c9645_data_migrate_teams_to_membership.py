# -*- coding: utf-8 -*-
"""data migrate checkin and admin teams to membership

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


class MEMBERSHIP_RECORD_TYPE:  # NOQA: N801
    INVITE = 0
    ACCEPT = 1
    DIRECT_ADD = 2
    AMEND = 3


profile = table(
    'profile',
    column('id', sa.Integer()),
    column('admin_team_id', sa.Integer()),
    column('uuid', UUIDType(binary=False)),
)

project = table(
    'project',
    column('id', sa.Integer()),
    column('profile_id', sa.Integer()),
    column('checkin_team_id', sa.Integer()),
    column('review_team_id', sa.Integer()),
    column('admin_team_id', sa.Integer()),
)

team = table(
    'team',
    column('id', sa.Integer()),
    column('owners', sa.Boolean()),
    column('org_uuid', UUIDType(binary=False)),
    column('created_at', sa.TIMESTAMP(timezone=True)),
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

profile_admin_membership = table(
    'profile_admin_membership',
    column('id', UUIDType(binary=False)),
    column('profile_id', sa.Integer()),
    column('user_id', sa.Integer()),
    column('is_owner', sa.Boolean()),
    column('granted_by_id', sa.Integer()),
    column('revoked_by_id', sa.Integer()),
    column('granted_at', sa.TIMESTAMP(timezone=True)),
    column('record_type', sa.Integer()),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('updated_at', sa.TIMESTAMP(timezone=True)),
    column('revoked_at', sa.TIMESTAMP(timezone=True)),
)


def upgrade():
    conn = op.get_bind()

    #: Create ProfileAdminMembership record for admin_team members of Profiles
    profiles = conn.execute(
        sa.select([profile.c.id, profile.c.admin_team_id, profile.c.uuid])
    )
    for profile_id, profile_admin_team_id, profile_uuid in profiles:
        owner_team_users = conn.execute(
            sa.select([users_teams.c.user_id, users_teams.c.created_at])
            .where(team.c.org_uuid == profile_uuid)
            .where(team.c.owners == 't')
            .where(users_teams.c.team_id == team.c.id)
        )
        owners_dict = {user_id: created_at for user_id, created_at in owner_team_users}
        admin_team_users = conn.execute(
            sa.select([users_teams.c.user_id, users_teams.c.created_at]).where(
                users_teams.c.team_id == profile_admin_team_id
            )
        )
        admins_dict = {user_id: created_at for user_id, created_at in admin_team_users}
        all_profile_admins = set(owners_dict.keys() + admins_dict.keys())

        for user_id in all_profile_admins:
            conn.execute(
                profile_admin_membership.insert().values(
                    {
                        'id': uuid4(),
                        'profile_id': profile_id,
                        'user_id': user_id,
                        'is_owner': user_id in owners_dict,
                        'granted_by_id': None,
                        'granted_at': (
                            owners_dict[user_id]
                            if user_id in owners_dict
                            else admins_dict[user_id]
                        ),
                        'record_type': MEMBERSHIP_RECORD_TYPE.DIRECT_ADD,
                        'created_at': sa.func.now(),
                        'updated_at': sa.func.now(),
                    }
                )
            )

    #: Create ProjectCrewMembership record for admin_team,
    # checkin_team and review_team members of Projects
    projects = conn.execute(
        sa.select(
            [
                project.c.id,
                project.c.checkin_team_id,
                project.c.review_team_id,
                project.c.admin_team_id,
            ]
        )
    )
    for project_id, checkin_team_id, review_team_id, admin_team_id in projects:
        # migrate checkin team
        checkin_team_users = conn.execute(
            sa.select([users_teams.c.user_id, users_teams.c.created_at]).where(
                users_teams.c.team_id == checkin_team_id
            )
        )
        checkin_dict = {
            user_id: created_at for user_id, created_at in checkin_team_users
        }
        review_team_users = conn.execute(
            sa.select([users_teams.c.user_id, users_teams.c.created_at]).where(
                users_teams.c.team_id == review_team_id
            )
        )
        review_dict = {user_id: created_at for user_id, created_at in review_team_users}
        admin_team_users = conn.execute(
            sa.select([users_teams.c.user_id, users_teams.c.created_at]).where(
                users_teams.c.team_id == admin_team_id
            )
        )
        admin_dict = {user_id: created_at for user_id, created_at in admin_team_users}
        all_users = set(checkin_dict.keys() + review_dict.keys() + admin_dict.keys())

        for user_id in all_users:
            conn.execute(
                project_crew_membership.insert().values(
                    {
                        'id': uuid4(),
                        'project_id': project_id,
                        'user_id': user_id,
                        #: admin and review team members become editors
                        'is_editor': user_id in admin_dict or user_id in review_dict,
                        #: admin team members become concierge
                        'is_concierge': user_id in admin_dict,
                        #: checkin team members become ushers
                        'is_usher': user_id in checkin_dict,
                        'granted_by_id': None,
                        'granted_at': (
                            checkin_dict[user_id]
                            if user_id in checkin_dict
                            else review_dict[user_id]
                            if user_id in review_dict
                            else admin_dict[user_id]
                        ),
                        'record_type': MEMBERSHIP_RECORD_TYPE.DIRECT_ADD,
                        'created_at': sa.func.now(),
                        'updated_at': sa.func.now(),
                    }
                )
            )


def downgrade():
    conn = op.get_bind()
    conn.execute(project_crew_membership.delete())
    conn.execute(profile_admin_membership.delete())
