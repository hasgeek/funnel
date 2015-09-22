"""add_title_to_ticket_type

Revision ID: 380089617763
Revises: 39eed1e99156
Create Date: 2015-09-14 19:29:00.133699

"""

# revision identifiers, used by Alembic.
revision = '380089617763'
down_revision = '39eed1e99156'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('ticket_type', sa.Column('title', sa.Unicode(length=250), nullable=True))
    op.create_unique_constraint("ticket_type_proposal_space_id_name", 'ticket_type', ['proposal_space_id', 'name'])


def downgrade():
    op.drop_constraint("ticket_type_proposal_space_id_name", 'ticket_type', type_='unique')
    op.drop_column('ticket_type', 'title')
