"""Move aside old user and team tables.

Revision ID: 09562978e3de
Revises: 321b11b6a413
Create Date: 2020-04-06 22:42:04.717152

"""

# revision identifiers, used by Alembic.
revision = '09562978e3de'
down_revision = '321b11b6a413'

import sqlalchemy as sa
from alembic import op

# (old, new)
renamed_tables = [
    ('user', 'old_user'),
    ('team', 'old_team'),
    ('users_teams', 'old_users_teams'),
]

# (old, new)
renamed_sequences = [
    ('user_id_seq', 'old_user_id_seq'),
    ('team_id_seq', 'old_team_id_seq'),
]


# (table, old, new)
renamed_columns = [
    ('old_users_teams', 'user_id', 'old_user_id'),
    ('old_users_teams', 'team_id', 'old_team_id'),
    ('comment', 'user_id', 'old_user_id'),
    ('contact_exchange', 'user_id', 'old_user_id'),
    ('participant', 'user_id', 'old_user_id'),
    ('project', 'user_id', 'old_user_id'),
    ('proposal', 'speaker_id', 'old_speaker_id'),
    ('proposal', 'user_id', 'old_user_id'),
    ('rsvp', 'user_id', 'old_user_id'),
    ('saved_project', 'user_id', 'old_user_id'),
    ('saved_session', 'user_id', 'old_user_id'),
    ('vote', 'user_id', 'old_user_id'),
    ('profile', 'admin_team_id', 'old_admin_team_id'),
    ('project', 'admin_team_id', 'old_admin_team_id'),
    ('project', 'checkin_team_id', 'old_checkin_team_id'),
    ('project', 'review_team_id', 'old_review_team_id'),
]

# (table, old, new)
renamed_constraints = [
    ('old_user', 'user_pkey', 'old_user_pkey'),
    ('old_user', 'user_email_key', 'old_user_email_key'),
    ('old_user', 'user_lastuser_token_key', 'old_user_lastuser_token_key'),
    ('old_user', 'user_username_key', 'old_user_username_key'),
    ('old_user', 'user_uuid_key', 'old_user_uuid_key'),
    ('old_team', 'team_pkey', 'old_team_pkey'),
    ('old_team', 'team_uuid_key', 'old_team_uuid_key'),
    ('old_users_teams', 'users_teams_pkey', 'old_users_teams_pkey'),
    ('old_users_teams', 'users_teams_team_id_fkey', 'old_users_teams_old_team_id_fkey'),
    ('old_users_teams', 'users_teams_user_id_fkey', 'old_users_teams_old_user_id_fkey'),
    ('comment', 'comment_user_id_fkey', 'comment_old_user_id_fkey'),
    (
        'contact_exchange',
        'contact_exchange_user_id_fkey',
        'contact_exchange_old_user_id_fkey',
    ),
    ('participant', 'participant_user_id_fkey', 'participant_old_user_id_fkey'),
    ('project', 'project_user_id_fkey', 'project_old_user_id_fkey'),
    ('proposal', 'proposal_speaker_id_fkey', 'proposal_old_speaker_id_fkey'),
    ('proposal', 'proposal_user_id_fkey', 'proposal_old_user_id_fkey'),
    ('rsvp', 'rsvp_user_id_fkey', 'rsvp_old_user_id_fkey'),
    ('saved_project', 'saved_project_user_id_fkey', 'saved_project_old_user_id_fkey'),
    ('saved_session', 'saved_session_user_id_fkey', 'saved_session_old_user_id_fkey'),
    ('vote', 'vote_user_id_fkey', 'vote_old_user_id_fkey'),
    ('vote', 'vote_user_id_voteset_id_key', 'vote_old_user_id_voteset_id_key'),
    ('profile', 'profile_admin_team_id_fkey', 'profile_old_admin_team_id_fkey'),
    ('project', 'project_admin_team_id_fkey', 'project_old_admin_team_id_fkey'),
    ('project', 'project_checkin_team_id_fkey', 'project_old_checkin_team_id_fkey'),
    ('project', 'project_review_team_id_fkey', 'project_old_review_team_id_fkey'),
]

# (old, new)
renamed_indexes = [('ix_team_org_uuid', 'ix_old_team_org_uuid')]


def upgrade() -> None:
    for old, new in renamed_tables:
        op.rename_table(old, new)

    for old, new in renamed_sequences:
        op.execute(sa.DDL(f'ALTER SEQUENCE "{old}" RENAME TO "{new}"'))

    for table, old, new in renamed_columns:
        op.alter_column(table, old, new_column_name=new)

    for table, old, new in renamed_constraints:
        op.execute(
            sa.DDL(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{old}" TO "{new}"')
        )

    for old, new in renamed_indexes:
        op.execute(sa.DDL(f'ALTER INDEX "{old}" RENAME TO "{new}"'))


def downgrade() -> None:
    for old, new in renamed_indexes:
        op.execute(sa.DDL(f'ALTER INDEX "{new}" RENAME TO "{old}"'))

    for table, old, new in renamed_constraints:
        op.execute(
            sa.DDL(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{new}" TO "{old}"')
        )

    for table, old, new in renamed_columns:
        op.alter_column(table, new, new_column_name=old)

    for old, new in renamed_sequences:
        op.execute(sa.DDL(f'ALTER SEQUENCE "{new}" RENAME TO "{old}"'))

    for old, new in renamed_tables:
        op.rename_table(new, old)
