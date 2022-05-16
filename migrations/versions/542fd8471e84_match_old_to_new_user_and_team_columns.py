"""Match old to new user and team columns.

Revision ID: 542fd8471e84
Revises: 382cde270594
Create Date: 2020-04-07 03:52:04.415019

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '542fd8471e84'
down_revision = '382cde270594'
branch_labels = None
depends_on = None

# (table, old, new)
migrate_user_columns = [
    ('comment', 'old_user_id', 'user_id'),
    ('contact_exchange', 'old_user_id', 'user_id'),
    ('participant', 'old_user_id', 'user_id'),
    ('project', 'old_user_id', 'user_id'),
    ('proposal', 'old_speaker_id', 'speaker_id'),
    ('proposal', 'old_user_id', 'user_id'),
    ('rsvp', 'old_user_id', 'user_id'),
    ('saved_project', 'old_user_id', 'user_id'),
    ('saved_session', 'old_user_id', 'user_id'),
    ('vote', 'old_user_id', 'user_id'),
]

# (table, old, new)
migrate_team_columns = [
    ('profile', 'old_admin_team_id', 'admin_team_id'),
    ('project', 'old_admin_team_id', 'admin_team_id'),
    ('project', 'old_checkin_team_id', 'checkin_team_id'),
    ('project', 'old_review_team_id', 'review_team_id'),
]


def upgrade():
    for table, old, new in migrate_user_columns:
        print(f"Upgrading {table}.{new}")
        op.execute(
            sa.DDL(
                f'''
                UPDATE "{table}" SET "{new}" = "user"."id"
                FROM "user", "old_user"
                WHERE "{table}"."{old}" = "old_user"."id"
                AND "old_user"."uuid" = "user"."uuid";
                '''
            )
        )

    for table, old, new in migrate_team_columns:
        print(f"Upgrading {table}.{new}")
        op.execute(
            sa.DDL(
                f'''
                UPDATE "{table}" SET "{new}" = "team"."id"
                FROM "team", "old_team"
                WHERE "{table}"."{old}" = "old_team"."id"
                AND "old_team"."uuid" = "team"."uuid";
                '''
            )
        )


def downgrade():
    pass
