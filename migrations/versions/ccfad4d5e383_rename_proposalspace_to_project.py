"""Rename ProposalSpace to Project.

Revision ID: ccfad4d5e383
Revises: 488077138ee4
Create Date: 2018-11-13 13:40:54.744756

"""

# revision identifiers, used by Alembic.
revision = 'ccfad4d5e383'
down_revision = '488077138ee4'

from alembic import op
import sqlalchemy as sa

# (old, new)
renamed_tables = [
    ('commentspace', 'commentset'),
    ('proposal_space', 'project'),
    ('proposal_space_redirect', 'project_redirect'),
    ('proposal_space_section', 'section'),
    ('votespace', 'voteset'),
]

# (old, new)
renamed_sequences = [
    ('commentspace_id_seq', 'commentset_id_seq'),
    ('proposal_space_id_seq', 'project_id_seq'),
    ('proposal_space_section_id_seq', 'section_id_seq'),
    ('votespace_id_seq', 'voteset_id_seq'),
]

# (table, old, new)
renamed_columns = [
    ('comment', 'status', 'state'),
    ('comment', 'commentspace_id', 'commentset_id'),
    ('comment', 'votes_id', 'voteset_id'),
    ('contact_exchange', 'proposal_space_id', 'project_id'),
    ('event', 'proposal_space_id', 'project_id'),
    ('participant', 'proposal_space_id', 'project_id'),
    ('project', 'status', 'state'),
    ('project', 'comments_id', 'commentset_id'),
    ('project', 'votes_id', 'voteset_id'),
    ('project', 'parent_space_id', 'parent_id'),
    ('project_redirect', 'proposal_space_id', 'project_id'),
    ('proposal', 'status', 'state'),
    ('proposal', 'proposal_space_id', 'project_id'),
    ('proposal', 'comments_id', 'commentset_id'),
    ('proposal', 'votes_id', 'voteset_id'),
    ('proposal_redirect', 'proposal_space_id', 'project_id'),
    ('rsvp', 'status', 'state'),
    ('rsvp', 'proposal_space_id', 'project_id'),
    ('section', 'comments_id', 'commentset_id'),
    ('section', 'proposal_space_id', 'project_id'),
    ('section', 'votes_id', 'voteset_id'),
    ('session', 'proposal_space_id', 'project_id'),
    ('ticket_client', 'proposal_space_id', 'project_id'),
    ('ticket_type', 'proposal_space_id', 'project_id'),
    ('user_group', 'proposal_space_id', 'project_id'),
    ('venue', 'proposal_space_id', 'project_id'),
    ('vote', 'votespace_id', 'voteset_id'),
]

# (table, old, new)
renamed_constraints = [
    ('comment', 'comment_commentspace_id_fkey', 'comment_commentset_id_fkey'),
    ('comment', 'comment_votes_id_fkey', 'comment_voteset_id_fkey'),
    ('comment', 'comment_status_check', 'comment_state_check'),
    ('commentset', 'commentspace_pkey', 'commentset_pkey'),
    (
        'contact_exchange',
        'contact_exchange_proposal_space_id_fkey',
        'contact_exchange_project_id_fkey',
    ),
    ('event', 'event_proposal_space_id_name_key', 'event_project_id_name_key'),
    ('event', 'event_proposal_space_id_title_key', 'event_project_id_title_key'),
    ('event', 'event_proposal_space_id_fkey', 'event_project_id_fkey'),
    (
        'participant',
        'participant_proposal_space_id_email_key',
        'participant_project_id_email_key',
    ),
    (
        'participant',
        'participant_proposal_space_id_fkey',
        'participant_project_id_fkey',
    ),
    ('project', 'proposal_space_name_check', 'project_name_check'),
    ('project', 'proposal_space_status_check', 'project_state_check'),
    ('project', 'proposal_space_legacy_name_key', 'project_legacy_name_key'),
    ('project', 'proposal_space_pkey', 'project_pkey'),
    ('project', 'proposal_space_profile_id_name_key', 'project_profile_id_name_key'),
    ('project', 'proposal_space_admin_team_id_fkey', 'project_admin_team_id_fkey'),
    ('project', 'proposal_space_review_team_id_fkey', 'project_review_team_id_fkey'),
    ('project', 'proposal_space_checkin_team_id_fkey', 'project_checkin_team_id_fkey'),
    ('project', 'proposal_space_comments_id_fkey', 'project_commentset_id_fkey'),
    ('project', 'proposal_space_votes_id_fkey', 'project_voteset_id_fkey'),
    ('project', 'proposal_space_parent_space_id_fkey', 'project_parent_id_fkey'),
    ('project', 'proposal_space_profile_id_fkey', 'project_profile_id_fkey'),
    ('project', 'proposal_space_user_id_fkey', 'project_user_id_fkey'),
    ('project_redirect', 'proposal_space_redirect_pkey', 'project_redirect_pkey'),
    (
        'project_redirect',
        'proposal_space_redirect_profile_id_fkey',
        'project_redirect_profile_id_fkey',
    ),
    (
        'project_redirect',
        'proposal_space_redirect_proposal_space_id_fkey',
        'project_redirect_project_id_fkey',
    ),
    ('proposal', 'proposal_status_check', 'proposal_state_check'),
    (
        'proposal',
        'proposal_proposal_space_id_url_id_key',
        'proposal_project_id_url_id_key',
    ),
    ('proposal', 'proposal_proposal_space_id_fkey', 'proposal_project_id_fkey'),
    ('proposal', 'proposal_comments_id_fkey', 'proposal_commentset_id_fkey'),
    ('proposal', 'proposal_votes_id_fkey', 'proposal_voteset_id_fkey'),
    (
        'proposal_redirect',
        'proposal_redirect_proposal_space_id_fkey',
        'proposal_redirect_project_id_fkey',
    ),
    ('rsvp', 'rsvp_status_check', 'rsvp_state_check'),
    ('rsvp', 'rsvp_proposal_space_id_fkey', 'rsvp_project_id_fkey'),
    ('section', 'proposal_space_section_name_check', 'section_name_check'),
    ('section', 'proposal_space_section_pkey', 'section_pkey'),
    (
        'section',
        'proposal_space_section_comments_id_fkey',
        'section_commentset_id_fkey',
    ),
    (
        'section',
        'proposal_space_section_proposal_space_id_fkey',
        'section_project_id_fkey',
    ),
    (
        'section',
        'proposal_space_section_proposal_space_id_name_key',
        'section_project_id_name_key',
    ),
    ('section', 'proposal_space_section_votes_id_fkey', 'section_voteset_id_fkey'),
    (
        'session',
        'session_proposal_space_id_url_id_key',
        'session_project_id_url_id_key',
    ),
    ('session', 'session_proposal_space_id_fkey', 'session_project_id_fkey'),
    (
        'ticket_client',
        'ticket_client_proposal_space_id_fkey',
        'ticket_client_project_id_fkey',
    ),
    (
        'ticket_type',
        'ticket_type_proposal_space_id_name_key',
        'ticket_type_project_id_name_key',
    ),
    (
        'ticket_type',
        'ticket_type_proposal_space_id_title_key',
        'ticket_type_project_id_title_key',
    ),
    (
        'ticket_type',
        'ticket_type_proposal_space_id_fkey',
        'ticket_type_project_id_fkey',
    ),
    (
        'user_group',
        'user_group_proposal_space_id_name_key',
        'user_group_project_id_name_key',
    ),
    ('user_group', 'user_group_proposal_space_id_fkey', 'user_group_project_id_fkey'),
    ('venue', 'venue_proposal_space_id_name_key', 'venue_project_id_name_key'),
    ('venue', 'venue_proposal_space_id_fkey', 'venue_project_id_fkey'),
    ('vote', 'vote_user_id_votespace_id_key', 'vote_user_id_voteset_id_key'),
    ('vote', 'vote_votespace_id_fkey', 'vote_voteset_id_fkey'),
    ('voteset', 'votespace_pkey', 'voteset_pkey'),
]


def upgrade():
    for old, new in renamed_tables:
        op.rename_table(old, new)

    for old, new in renamed_sequences:
        op.execute(sa.DDL(f'ALTER SEQUENCE {old} RENAME TO {new}'))

    for table, old, new in renamed_columns:
        op.alter_column(table, old, new_column_name=new)

    for table, old, new in renamed_constraints:
        op.execute(
            sa.DDL(
                'ALTER TABLE {table} RENAME CONSTRAINT {old} TO {new}'.format(
                    table=table, old=old, new=new
                )
            )
        )


def downgrade():
    for table, old, new in renamed_constraints:
        op.execute(
            sa.DDL(
                'ALTER TABLE {table} RENAME CONSTRAINT {new} TO {old}'.format(
                    table=table, old=old, new=new
                )
            )
        )

    for table, old, new in renamed_columns:
        op.alter_column(table, new, new_column_name=old)

    for old, new in renamed_sequences:
        op.execute(sa.DDL(f'ALTER SEQUENCE {new} RENAME TO {old}'))

    for old, new in renamed_tables:
        op.rename_table(new, old)
