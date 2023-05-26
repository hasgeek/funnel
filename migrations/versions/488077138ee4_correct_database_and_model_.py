# type: ignore
"""Correct database and model inconsistencies.

Revision ID: 488077138ee4
Revises: 2cbfbcca4737
Create Date: 2018-11-12 13:54:09.987761

"""

# revision identifiers, used by Alembic.
revision = '488077138ee4'
down_revision = '2cbfbcca4737'

from alembic import op
from sqlalchemy.schema import CreateSequence, DropSequence, Sequence
import sqlalchemy as sa

from coaster.sqlalchemy import JsonDict

tables_with_name_column = [
    'event',
    'profile',
    'proposal',
    'proposal_space',
    'proposal_space_section',
    'session',
    'ticket_type',
    'user_group',
    'venue',
    'venue_room',
]


def upgrade() -> None:
    for tablename in tables_with_name_column:
        # Create CHECK constraint on name
        op.create_check_constraint(tablename + '_name_check', tablename, "name <> ''")

    # RENAME CONSTRAINT works in PostgreSQL >= 9.2
    op.execute(
        sa.DDL(
            'ALTER TABLE comment RENAME CONSTRAINT ck_comment_state_valid TO comment_status_check;'
        )
    )
    op.execute(
        sa.DDL(
            'ALTER TABLE proposal RENAME CONSTRAINT ck_proposal_state_valid TO proposal_status_check;'
        )
    )
    op.execute(
        sa.DDL(
            'ALTER TABLE proposal_space RENAME CONSTRAINT ck_proposal_space_state_valid TO proposal_space_status_check;'
        )
    )
    op.execute(
        sa.DDL(
            'ALTER TABLE rsvp RENAME CONSTRAINT ck_rsvp_state_valid TO rsvp_status_check;'
        )
    )
    op.execute(
        sa.DDL(
            'ALTER TABLE contact_exchange RENAME CONSTRAINT contact_exchange_user_id_proposal_space_id_participant_id_key TO contact_exchange_pkey;'
        )
    )
    op.execute(
        sa.DDL(
            'ALTER TABLE proposal_space RENAME CONSTRAINT proposal_space_proposal_space_id_fkey TO proposal_space_parent_space_id_fkey;'
        )
    )

    op.alter_column(
        'proposal_redirect', 'url_id', existing_type=sa.INTEGER(), server_default=None
    )
    op.execute(DropSequence(Sequence('proposal_redirect_url_id_seq')))

    op.alter_column(
        'user',
        'userinfo',
        type_=JsonDict(),
        existing_type=sa.TEXT(),
        postgresql_using='userinfo::jsonb',
    )


def downgrade() -> None:
    op.alter_column('user', 'userinfo', type_=sa.TEXT(), existing_type=JsonDict())

    op.execute(CreateSequence(Sequence('proposal_redirect_url_id_seq')))
    op.execute(
        sa.DDL(
            'ALTER SEQUENCE proposal_redirect_url_id_seq OWNED BY proposal_redirect.url_id;'
        )
    )
    op.execute(
        sa.DDL(
            "ALTER TABLE ONLY proposal_redirect ALTER COLUMN url_id SET DEFAULT nextval('proposal_redirect_url_id_seq'::regclass);"
        )
    )

    # RENAME CONSTRAINT works in PostgreSQL >= 9.2
    op.execute(
        sa.DDL(
            'ALTER TABLE proposal_space RENAME CONSTRAINT proposal_space_parent_space_id_fkey TO proposal_space_proposal_space_id_fkey;'
        )
    )
    op.execute(
        sa.DDL(
            'ALTER TABLE contact_exchange RENAME CONSTRAINT contact_exchange_pkey TO contact_exchange_user_id_proposal_space_id_participant_id_key;'
        )
    )
    op.execute(
        sa.DDL(
            'ALTER TABLE rsvp RENAME CONSTRAINT rsvp_status_check TO ck_rsvp_state_valid;'
        )
    )
    op.execute(
        sa.DDL(
            'ALTER TABLE proposal_space RENAME CONSTRAINT proposal_space_status_check TO ck_proposal_space_state_valid;'
        )
    )
    op.execute(
        sa.DDL(
            'ALTER TABLE proposal RENAME CONSTRAINT proposal_status_check TO ck_proposal_state_valid;'
        )
    )
    op.execute(
        sa.DDL(
            'ALTER TABLE comment RENAME CONSTRAINT comment_status_check TO ck_comment_state_valid;'
        )
    )

    for tablename in tables_with_name_column:
        # Drop CHECK constraint on name
        op.drop_constraint(tablename + '_name_check', tablename)
