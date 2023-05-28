"""Contact exchange cascades.

Revision ID: 252f9a705901
Revises: 034863dbaac2
Create Date: 2019-05-16 16:55:46.629413

"""

# revision identifiers, used by Alembic.
revision = '252f9a705901'
down_revision = '034863dbaac2'

from alembic import op


def upgrade() -> None:
    op.drop_constraint(
        'contact_exchange_user_id_fkey', 'contact_exchange', type_='foreignkey'
    )
    op.drop_constraint(
        'contact_exchange_project_id_fkey', 'contact_exchange', type_='foreignkey'
    )
    op.drop_constraint(
        'contact_exchange_participant_id_fkey', 'contact_exchange', type_='foreignkey'
    )
    op.create_foreign_key(
        'contact_exchange_user_id_fkey',
        'contact_exchange',
        'user',
        ['user_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'contact_exchange_project_id_fkey',
        'contact_exchange',
        'project',
        ['project_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        'contact_exchange_participant_id_fkey',
        'contact_exchange',
        'participant',
        ['participant_id'],
        ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint(
        'contact_exchange_participant_id_fkey', 'contact_exchange', type_='foreignkey'
    )
    op.drop_constraint(
        'contact_exchange_project_id_fkey', 'contact_exchange', type_='foreignkey'
    )
    op.drop_constraint(
        'contact_exchange_user_id_fkey', 'contact_exchange', type_='foreignkey'
    )
    op.create_foreign_key(
        'contact_exchange_participant_id_fkey',
        'contact_exchange',
        'participant',
        ['participant_id'],
        ['id'],
    )
    op.create_foreign_key(
        'contact_exchange_project_id_fkey',
        'contact_exchange',
        'project',
        ['project_id'],
        ['id'],
    )
    op.create_foreign_key(
        'contact_exchange_user_id_fkey', 'contact_exchange', 'user', ['user_id'], ['id']
    )
