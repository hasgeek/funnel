"""Drop old user and team columns.

Revision ID: 62d770006955
Revises: 542fd8471e84
Create Date: 2020-04-07 04:14:29.626224

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '62d770006955'
down_revision = '542fd8471e84'
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
    op.drop_constraint('comment_old_user_id_fkey', 'comment', type_='foreignkey')
    op.drop_column('comment', 'old_user_id')

    op.drop_constraint('contact_exchange_pkey', 'contact_exchange', type_='primary')
    op.drop_constraint(
        'contact_exchange_old_user_id_fkey', 'contact_exchange', type_='foreignkey'
    )
    op.drop_column('contact_exchange', 'old_user_id')
    op.alter_column('contact_exchange', 'user_id', nullable=False)
    op.create_primary_key(
        'contact_exchange_pkey', 'contact_exchange', ['user_id', 'participant_id']
    )

    op.create_foreign_key(
        'organization_owners_id_fkey',
        'organization',
        'team',
        ['owners_id'],
        ['id'],
        use_alter=True,
    )

    op.drop_constraint(
        'participant_old_user_id_fkey', 'participant', type_='foreignkey'
    )
    op.drop_column('participant', 'old_user_id')

    op.drop_constraint('profile_old_admin_team_id_fkey', 'profile', type_='foreignkey')
    op.drop_column('profile', 'old_admin_team_id')

    op.alter_column('project', 'user_id', existing_type=sa.INTEGER(), nullable=False)
    op.drop_constraint(
        'project_old_checkin_team_id_fkey', 'project', type_='foreignkey'
    )
    op.drop_constraint('project_old_admin_team_id_fkey', 'project', type_='foreignkey')
    op.drop_constraint('project_old_review_team_id_fkey', 'project', type_='foreignkey')
    op.drop_constraint('project_old_user_id_fkey', 'project', type_='foreignkey')
    op.drop_column('project', 'old_user_id')
    op.drop_column('project', 'old_checkin_team_id')
    op.drop_column('project', 'old_review_team_id')
    op.drop_column('project', 'old_admin_team_id')

    op.alter_column('proposal', 'user_id', existing_type=sa.INTEGER(), nullable=False)
    op.drop_constraint('proposal_old_user_id_fkey', 'proposal', type_='foreignkey')
    op.drop_constraint('proposal_old_speaker_id_fkey', 'proposal', type_='foreignkey')
    op.drop_column('proposal', 'old_user_id')
    op.drop_column('proposal', 'old_speaker_id')

    op.drop_constraint('rsvp_pkey', 'rsvp', type_='primary')
    op.drop_constraint('rsvp_old_user_id_fkey', 'rsvp', type_='foreignkey')
    op.drop_column('rsvp', 'old_user_id')
    op.alter_column('rsvp', 'user_id', nullable=False)
    op.create_primary_key('rsvp_pkey', 'rsvp', ['project_id', 'user_id'])

    op.drop_constraint('saved_project_pkey', 'saved_project', type_='primary')
    op.drop_constraint(
        'saved_project_old_user_id_fkey', 'saved_project', type_='foreignkey'
    )
    op.drop_column('saved_project', 'old_user_id')
    op.alter_column('saved_project', 'user_id', nullable=False)
    op.create_primary_key(
        'saved_project_pkey', 'saved_project', ['user_id', 'project_id']
    )

    op.drop_constraint('saved_session_pkey', 'saved_session', type_='primary')
    op.drop_constraint(
        'saved_session_old_user_id_fkey', 'saved_session', type_='foreignkey'
    )
    op.drop_column('saved_session', 'old_user_id')
    op.alter_column('saved_session', 'user_id', nullable=False)
    op.create_primary_key(
        'saved_session_pkey', 'saved_session', ['user_id', 'session_id']
    )

    op.alter_column('vote', 'user_id', existing_type=sa.INTEGER(), nullable=False)
    op.drop_constraint('vote_old_user_id_voteset_id_key', 'vote', type_='unique')
    op.drop_constraint('vote_old_user_id_fkey', 'vote', type_='foreignkey')
    op.drop_column('vote', 'old_user_id')


def downgrade():
    op.add_column(
        'vote',
        sa.Column('old_user_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        'vote_old_user_id_fkey', 'vote', 'old_user', ['old_user_id'], ['id']
    )
    op.create_unique_constraint(
        'vote_old_user_id_voteset_id_key', 'vote', ['old_user_id', 'voteset_id']
    )
    op.alter_column('vote', 'user_id', existing_type=sa.INTEGER(), nullable=True)
    op.add_column(
        'saved_session',
        sa.Column('old_user_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        'saved_session_old_user_id_fkey',
        'saved_session',
        'old_user',
        ['old_user_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.add_column(
        'saved_project',
        sa.Column('old_user_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        'saved_project_old_user_id_fkey',
        'saved_project',
        'old_user',
        ['old_user_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.add_column(
        'rsvp',
        sa.Column('old_user_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        'rsvp_old_user_id_fkey', 'rsvp', 'old_user', ['old_user_id'], ['id']
    )
    op.add_column(
        'proposal',
        sa.Column('old_speaker_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.add_column(
        'proposal',
        sa.Column('old_user_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        'proposal_old_speaker_id_fkey',
        'proposal',
        'old_user',
        ['old_speaker_id'],
        ['id'],
    )
    op.create_foreign_key(
        'proposal_old_user_id_fkey', 'proposal', 'old_user', ['old_user_id'], ['id']
    )
    op.alter_column('proposal', 'user_id', existing_type=sa.INTEGER(), nullable=True)
    op.add_column(
        'project',
        sa.Column(
            'old_admin_team_id', sa.INTEGER(), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        'project',
        sa.Column(
            'old_review_team_id', sa.INTEGER(), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        'project',
        sa.Column(
            'old_checkin_team_id', sa.INTEGER(), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        'project',
        sa.Column('old_user_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        'project_old_user_id_fkey', 'project', 'old_user', ['old_user_id'], ['id']
    )
    op.create_foreign_key(
        'project_old_review_team_id_fkey',
        'project',
        'old_team',
        ['old_review_team_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'project_old_admin_team_id_fkey',
        'project',
        'old_team',
        ['old_admin_team_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        'project_old_checkin_team_id_fkey',
        'project',
        'old_team',
        ['old_checkin_team_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.alter_column('project', 'user_id', existing_type=sa.INTEGER(), nullable=True)
    op.add_column(
        'profile',
        sa.Column(
            'old_admin_team_id', sa.INTEGER(), autoincrement=False, nullable=True
        ),
    )
    op.create_foreign_key(
        'profile_old_admin_team_id_fkey',
        'profile',
        'old_team',
        ['old_admin_team_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.add_column(
        'participant',
        sa.Column('old_user_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        'participant_old_user_id_fkey',
        'participant',
        'old_user',
        ['old_user_id'],
        ['id'],
    )
    op.drop_constraint(
        'organization_owners_id_fkey', 'organization', type_='foreignkey'
    )
    op.add_column(
        'contact_exchange',
        sa.Column('old_user_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        'contact_exchange_old_user_id_fkey',
        'contact_exchange',
        'old_user',
        ['old_user_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.add_column(
        'comment',
        sa.Column('old_user_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        'comment_old_user_id_fkey', 'comment', 'old_user', ['old_user_id'], ['id']
    )

    # Migrate column data
    for table, old, new in migrate_user_columns:
        print(f"Restoring {table}.{old}")
        op.execute(
            sa.DDL(
                f'''
                UPDATE "{table}" SET "{old}" = "old_user"."id"
                FROM "user", "old_user"
                WHERE "{table}"."{new}" = "user"."id"
                AND "user"."uuid" = "old_user"."uuid";
                '''
            )
        )

    for table, old, new in migrate_team_columns:
        print(f"Restoring {table}.{old}")
        op.execute(
            sa.DDL(
                f'''
                UPDATE "{table}" SET "{old}" = "old_team"."id"
                FROM "team", "old_team"
                WHERE "{table}"."{new}" = "team"."id"
                AND "team"."uuid" = "old_team"."uuid";
                '''
            )
        )

    # Alter columns to make nullable=False and restore old composite primary keys
    op.alter_column('vote', 'old_user_id', nullable=False)

    op.alter_column('saved_session', 'old_user_id', nullable=False)
    op.drop_constraint('saved_session_pkey', 'saved_session', type_='primary')
    op.create_primary_key(
        'saved_session_pkey', 'saved_session', ['user_id', 'session_id']
    )

    op.alter_column('saved_project', 'old_user_id', nullable=False)
    op.drop_constraint('saved_project_pkey', 'saved_project', type_='primary')
    op.create_primary_key(
        'saved_project_pkey', 'saved_project', ['old_user_id', 'project_id']
    )

    op.alter_column('rsvp', 'old_user_id', nullable=False)
    op.drop_constraint('rsvp_pkey', 'rsvp', type_='primary')
    op.create_primary_key('rsvp_pkey', 'rsvp', ['project_id', 'old_user_id'])

    op.alter_column('proposal', 'old_user_id', nullable=False)

    op.alter_column('project', 'old_user_id', nullable=False)

    op.alter_column('contact_exchange', 'old_user_id', nullable=False)
    op.drop_constraint('contact_exchange_pkey', 'contact_exchange', type_='primary')
    op.create_primary_key(
        'contact_exchange_pkey', 'contact_exchange', ['old_user_id', 'participant_id']
    )
