"""Remove id from contact_exchange, use composite primary key.

Revision ID: 4083b7bd0cc8
Revises: 22fb4e1e3139
Create Date: 2015-07-06 17:42:40.175382
"""

# revision identifiers, used by Alembic.
revision = '4083b7bd0cc8'
down_revision = '22fb4e1e3139'

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.drop_constraint(
        'contact_exchange_user_id_proposal_space_id_participant_id_key',
        'contact_exchange',
        type_='unique',
    )
    op.drop_column('contact_exchange', 'id')
    op.create_primary_key(
        'contact_exchange_user_id_proposal_space_id_participant_id_pk',
        'contact_exchange',
        ['user_id', 'proposal_space_id', 'participant_id'],
    )


def downgrade() -> None:
    op.add_column('contact_exchange', sa.Column('id', sa.INTEGER(), nullable=False))
    op.drop_constraint(
        'contact_exchange_user_id_proposal_space_id_participant_id_pk',
        'contact_exchange',
        type_='primary',
    )
    op.create_unique_constraint(
        'contact_exchange_user_id_proposal_space_id_participant_id_key',
        'contact_exchange',
        ['user_id', 'proposal_space_id', 'participant_id'],
    )
