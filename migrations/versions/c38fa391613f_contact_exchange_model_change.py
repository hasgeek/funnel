"""Contact exchange model change

Revision ID: c38fa391613f
Revises: 252f9a705901
Create Date: 2019-05-20 14:41:42.347664

"""

# revision identifiers, used by Alembic.
revision = 'c38fa391613f'
down_revision = '252f9a705901'

from alembic import op
import sqlalchemy as sa  # NOQA


def upgrade():
    # Remove duplicate entries before dropping the project_id column
    op.execute(sa.DDL('''
        DELETE FROM contact_exchange WHERE (user_id, project_id, participant_id) IN (
            SELECT user_id, project_id, participant_id
            FROM (SELECT user_id, project_id, participant_id, row_number()
                OVER (partition by user_id, participant_id ORDER BY created_at)
                FROM contact_exchange) AS duplicates
            WHERE row_number != 1);
    '''))
    # Index by participant id
    op.create_index(op.f('ix_contact_exchange_participant_id'),
        'contact_exchange', ['participant_id'], unique=False)
    # Drop the primary key
    op.drop_constraint('contact_exchange_pkey', 'contact_exchange', type_='primary')
    # Recreate primary key without project_id
    op.create_primary_key('contact_exchange_pkey', 'contact_exchange',
        ['user_id', 'participant_id'])
    # Finally, drop the project_id foreign key constraint and then the column itself
    op.drop_constraint('contact_exchange_project_id_fkey', 'contact_exchange', type_='foreignkey')
    op.drop_column('contact_exchange', 'project_id')


def downgrade():
    # Re-add project_id column and populate it from participant.project_id,
    # then make it a foreign key
    op.add_column('contact_exchange',
        sa.Column('project_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.execute(sa.DDL('''
        UPDATE contact_exchange
        SET project_id = participant.project_id
        FROM participant
        WHERE contact_exchange.participant_id = participant.id
        '''))
    op.alter_column('contact_exchange', 'project_id', nullable=False)
    op.create_foreign_key(u'contact_exchange_project_id_fkey', 'contact_exchange', 'project', ['project_id'], ['id'], ondelete=u'CASCADE')
    # Recreate primary key to include project id
    op.drop_constraint('contact_exchange_pkey', 'contact_exchange', type_='primary')
    op.create_primary_key('contact_exchange_pkey', 'contact_exchange',
        ['user_id', 'project_id', 'participant_id'])
    # Drop the participant index we created in the upgrade
    op.drop_index(op.f('ix_contact_exchange_participant_id'), table_name='contact_exchange')
