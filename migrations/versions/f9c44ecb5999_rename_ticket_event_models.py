"""Rename ticket event models.

Revision ID: f9c44ecb5999
Revises: 74e1fbb4a948
Create Date: 2020-09-10 02:13:29.641181

"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f9c44ecb5999'
down_revision = '74e1fbb4a948'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None

# (old, new)
renamed_tables = [
    ('event', 'ticket_event'),
    ('participant', 'ticket_participant'),
    ('attendee', 'ticket_event_participant'),
    ('event_ticket_type', 'ticket_event_ticket_type'),
]

# (old, new)
renamed_sequences = [
    ('event_id_seq', 'ticket_event_id_seq'),
    ('participant_id_seq', 'ticket_participant_id_seq'),
    ('attendee_id_seq', 'ticket_event_participant_id_seq'),
]


# (table, old, new)
renamed_columns = [
    ('ticket_event_participant', 'participant_id', 'ticket_participant_id'),
    ('ticket_event_participant', 'event_id', 'ticket_event_id'),
    ('ticket_event_ticket_type', 'event_id', 'ticket_event_id'),
    ('contact_exchange', 'participant_id', 'ticket_participant_id'),
    ('sync_ticket', 'participant_id', 'ticket_participant_id'),
]

# (table, old, new)
renamed_constraints = [
    ('ticket_event', 'event_pkey', 'ticket_event_pkey'),
    ('ticket_event', 'event_project_id_name_key', 'ticket_event_project_id_name_key'),
    ('ticket_event', 'event_project_id_title_key', 'ticket_event_project_id_title_key'),
    ('ticket_event', 'event_name_check', 'ticket_event_name_check'),
    ('ticket_event', 'event_project_id_fkey', 'ticket_event_project_id_fkey'),
    ('ticket_participant', 'participant_pkey', 'ticket_participant_pkey'),
    ('ticket_participant', 'participant_key_key', 'ticket_participant_key_key'),
    (
        'ticket_participant',
        'participant_project_id_email_address_id_key',
        'ticket_participant_project_id_email_address_id_key',
    ),
    ('ticket_participant', 'participant_puk_key', 'ticket_participant_puk_key'),
    ('ticket_participant', 'participant_uuid_key', 'ticket_participant_uuid_key'),
    (
        'ticket_participant',
        'participant_email_address_id_fkey',
        'ticket_participant_email_address_id_fkey',
    ),
    (
        'ticket_participant',
        'participant_project_id_fkey',
        'ticket_participant_project_id_fkey',
    ),
    (
        'ticket_participant',
        'participant_user_id_fkey',
        'ticket_participant_user_id_fkey',
    ),
    ('ticket_event_participant', 'attendee_pkey', 'ticket_event_participant_pkey'),
    (
        'ticket_event_participant',
        'attendee_event_id_participant_id_key',
        'ticket_event_participant_event_id_participant_id_key',
    ),
    (
        'ticket_event_participant',
        'attendee_event_id_fkey',
        'ticket_event_participant_ticket_event_id_fkey',
    ),
    (
        'ticket_event_participant',
        'attendee_participant_id_fkey',
        'ticket_event_participant_ticket_participant_id_fkey',
    ),
    (
        'ticket_event_ticket_type',
        'event_ticket_type_pkey',
        'ticket_event_ticket_type_pkey',
    ),
    (
        'ticket_event_ticket_type',
        'event_ticket_type_event_id_fkey',
        'ticket_event_ticket_type_ticket_event_id_fkey',
    ),
    (
        'ticket_event_ticket_type',
        'event_ticket_type_ticket_type_id_fkey',
        'ticket_event_ticket_type_ticket_type_id_fkey',
    ),
    (
        'sync_ticket',
        'sync_ticket_participant_id_fkey',
        'sync_ticket_ticket_participant_id_fkey',
    ),
    (
        'contact_exchange',
        'contact_exchange_participant_id_fkey',
        'contact_exchange_ticket_participant_id_fkey',
    ),
]

# (old, new)
renamed_indexes = [
    ('ix_participant_email_address_id', 'ix_ticket_participant_email_address_id'),
    ('ix_contact_exchange_participant_id', 'ix_contact_exchange_ticket_participant_id'),
]


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
