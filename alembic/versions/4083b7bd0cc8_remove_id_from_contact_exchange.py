"""remove_id_from_contact_exchange_use_composite_primary_key
Revision ID: 4083b7bd0cc8
Revises: 22fb4e1e3139
Create Date: 2015-07-06 17:42:40.175382
"""

# revision identifiers, used by Alembic.
revision = '4083b7bd0cc8'
down_revision = '22fb4e1e3139'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_constraint(u'contact_exchange_user_id_proposal_space_id_participant_id_key', 'contact_exchange', type_='unique')
    op.drop_column('contact_exchange', 'id')
    op.create_primary_key(u'contact_exchange_user_id_proposal_space_id_participant_id_pk', 'contact_exchange', ['user_id', 'proposal_space_id', 'participant_id'])


def downgrade():
    op.add_column('contact_exchange', sa.Column('id', sa.INTEGER(), nullable=False))
    op.drop_constraint(u'contact_exchange_user_id_proposal_space_id_participant_id_pk', 'contact_exchange', type_='primary')
    op.create_unique_constraint(u'contact_exchange_user_id_proposal_space_id_participant_id_key', 'contact_exchange', ['user_id', 'proposal_space_id', 'participant_id'])
