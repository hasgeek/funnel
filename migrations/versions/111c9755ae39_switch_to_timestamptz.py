"""Switch to timestamptz

Revision ID: 111c9755ae39
Revises: e679554261b2
Create Date: 2019-05-09 19:01:53.976390

"""

# revision identifiers, used by Alembic.
revision = '111c9755ae39'
down_revision = 'e679554261b2'

from alembic import op
import sqlalchemy as sa  # NOQA


migrate_table_columns = [
    ('attendee', 'created_at'),
    ('attendee', 'updated_at'),
    ('comment', 'created_at'),
    ('comment', 'updated_at'),
    ('comment', 'edited_at'),
    ('commentset', 'created_at'),
    ('commentset', 'updated_at'),
    ('contact_exchange', 'created_at'),
    ('contact_exchange', 'updated_at'),
    ('draft', 'created_at'),
    ('draft', 'updated_at'),
    ('event', 'created_at'),
    ('event', 'updated_at'),
    ('event_ticket_type', 'created_at'),
    ('label', 'created_at'),
    ('label', 'updated_at'),
    ('participant', 'created_at'),
    ('participant', 'updated_at'),
    ('profile', 'created_at'),
    ('profile', 'updated_at'),
    ('project', 'created_at'),
    ('project', 'updated_at'),
    ('project', 'cfp_start_at'),
    ('project', 'cfp_end_at'),
    ('project_location', 'created_at'),
    ('project_location', 'updated_at'),
    ('project_redirect', 'created_at'),
    ('project_redirect', 'updated_at'),
    ('project_venue_primary', 'created_at'),
    ('project_venue_primary', 'updated_at'),
    ('proposal', 'created_at'),
    ('proposal', 'updated_at'),
    ('proposal', 'edited_at'),
    ('proposal_feedback', 'created_at'),
    ('proposal_feedback', 'updated_at'),
    ('proposal_label', 'created_at'),
    ('proposal_redirect', 'created_at'),
    ('proposal_redirect', 'updated_at'),
    ('rsvp', 'created_at'),
    ('rsvp', 'updated_at'),
    ('section', 'created_at'),
    ('section', 'updated_at'),
    ('session', 'created_at'),
    ('session', 'updated_at'),
    ('session', 'start'),
    ('session', 'end'),
    ('sync_ticket', 'created_at'),
    ('sync_ticket', 'updated_at'),
    ('team', 'created_at'),
    ('team', 'updated_at'),
    ('ticket_client', 'created_at'),
    ('ticket_client', 'updated_at'),
    ('ticket_type', 'created_at'),
    ('ticket_type', 'updated_at'),
    ('user', 'created_at'),
    ('user', 'updated_at'),
    ('users_teams', 'created_at'),
    ('users_teams', 'updated_at'),
    ('venue', 'created_at'),
    ('venue', 'updated_at'),
    ('venue_room', 'created_at'),
    ('venue_room', 'updated_at'),
    ('vote', 'created_at'),
    ('vote', 'updated_at'),
    ('voteset', 'created_at'),
    ('voteset', 'updated_at'),
    ]


def upgrade():
    for table, column in migrate_table_columns:
        op.execute(sa.DDL(
            'ALTER TABLE "%(table)s" ALTER COLUMN "%(column)s" TYPE TIMESTAMP WITH TIME ZONE USING "%(column)s" AT TIME ZONE \'UTC\'',
            context={'table': table, 'column': column}
            ))


def downgrade():
    for table, column in reversed(migrate_table_columns):
        op.execute(sa.DDL(
            'ALTER TABLE "%(table)s" ALTER COLUMN "%(column)s" TYPE TIMESTAMP WITHOUT TIME ZONE',
            context={'table': table, 'column': column}
            ))
