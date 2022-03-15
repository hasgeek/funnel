"""Populate membership models.

Revision ID: 71fcac85957c
Revises: 8829241430b6
Create Date: 2020-04-21 02:01:52.012077

"""

from uuid import uuid4

from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import column, table
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '71fcac85957c'
down_revision = '8829241430b6'
branch_labels = None
depends_on = None


class MEMBERSHIP_RECORD_TYPE:
    INVITE = 0
    ACCEPT = 1
    DIRECT_ADD = 2
    AMEND = 3


organization = table(
    'organization',
    column('id', sa.Integer()),
    column('owners_id', sa.Integer()),
    column('uuid', postgresql.UUID(as_uuid=True)),
)

profile = table(
    'profile',
    column('id', sa.Integer()),
    column('uuid', postgresql.UUID(as_uuid=True)),
    column('user_id', sa.Integer()),
    column('organization_id', sa.Integer()),
    column('admin_team_id', sa.Integer()),
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
    column('organization_id', sa.Integer()),
    column('created_at', sa.TIMESTAMP(timezone=True)),
)

team_membership = table(
    'team_membership',
    column('user_id', sa.Integer()),
    column('team_id', sa.Integer()),
    column('created_at', sa.TIMESTAMP(timezone=True)),
)

proposal = table(
    'proposal',
    column('id', sa.Integer()),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('user_id', sa.Integer()),
    column('speaker_id', sa.Integer()),
)

project_crew_membership = table(
    'project_crew_membership',
    column('id', postgresql.UUID(as_uuid=True)),
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

organization_membership = table(
    'organization_membership',
    column('id', postgresql.UUID(as_uuid=True)),
    column('organization_id', sa.Integer()),
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

proposal_membership = table(
    'proposal_membership',
    column('id', postgresql.UUID(as_uuid=True)),
    column('proposal_id', sa.Integer()),
    column('user_id', sa.Integer()),
    column('is_reviewer', sa.Boolean()),
    column('is_speaker', sa.Boolean()),
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

    #: Create OrganizationMembership record for owners team members of Organization
    orgs = conn.execute(sa.select([organization.c.id, organization.c.owners_id]))
    for org_id, org_owners_id in orgs:
        owner_team_users = conn.execute(
            sa.select([team_membership.c.user_id, team_membership.c.created_at])
            .where(team.c.id == org_owners_id)
            .where(team_membership.c.team_id == team.c.id)
        )
        owners_dict = {user_id: created_at for user_id, created_at in owner_team_users}
        admin_team_users = conn.execute(
            sa.select([team_membership.c.user_id, team_membership.c.created_at])
            .where(profile.c.organization_id == org_id)
            .where(team_membership.c.team_id == profile.c.admin_team_id)
        )
        admins_dict = {user_id: created_at for user_id, created_at in admin_team_users}
        all_profile_admins = set(owners_dict.keys()) | set(admins_dict.keys())

        for user_id in all_profile_admins:
            conn.execute(
                organization_membership.insert().values(
                    {
                        'id': uuid4(),
                        'organization_id': org_id,
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
        checkin_team_users = conn.execute(
            sa.select([team_membership.c.user_id, team_membership.c.created_at]).where(
                team_membership.c.team_id == checkin_team_id
            )
        )
        checkin_dict = {
            user_id: created_at for user_id, created_at in checkin_team_users
        }
        review_team_users = conn.execute(
            sa.select([team_membership.c.user_id, team_membership.c.created_at]).where(
                team_membership.c.team_id == review_team_id
            )
        )
        review_dict = {user_id: created_at for user_id, created_at in review_team_users}
        admin_team_users = conn.execute(
            sa.select([team_membership.c.user_id, team_membership.c.created_at]).where(
                team_membership.c.team_id == admin_team_id
            )
        )
        admin_dict = {user_id: created_at for user_id, created_at in admin_team_users}
        all_users = (
            set(checkin_dict.keys()) | set(review_dict.keys()) | set(admin_dict.keys())
        )

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
                            admin_dict[user_id]
                            if user_id in admin_dict
                            else checkin_dict[user_id]
                            if user_id in checkin_dict
                            else review_dict[user_id]
                            if user_id in review_dict
                            else sa.func.now()
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
    conn.execute(organization_membership.delete())
