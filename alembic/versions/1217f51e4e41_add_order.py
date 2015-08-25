"""add order

Revision ID: 1217f51e4e41
Revises: 39eed1e99156
Create Date: 2015-08-21 20:18:20.102053

"""

revision = '1217f51e4e41'
down_revision = '39eed1e99156'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('order',
    sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('order_no', sa.Unicode(length=80), nullable=False),
        sa.Column('proposal_space_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('ticket_client_id', sa.Integer(), nullable=True),
        sa.Column('buyer_email', sa.Unicode(length=80), nullable=True),
        sa.Column('buyer_phone', sa.Unicode(length=80), nullable=True),
        sa.Column('purchased_at', sa.DateTime(), nullable=False),
        sa.Column('company_name', sa.Unicode(length=80), nullable=True),
        sa.Column('paid_amount', sa.Numeric(), nullable=False),
        sa.Column('refund_amount', sa.Numeric(), nullable=False),
        sa.Column('payment_confirmed', sa.Boolean(), nullable=False),
        sa.CheckConstraint(u'paid_amount > refund_amount', name='payment_greater_than_refund'),
        sa.ForeignKeyConstraint(['proposal_space_id'], ['proposal_space.id'], ),
        sa.ForeignKeyConstraint(['ticket_client_id'], ['ticket_client.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('proposal_space_id', 'order_no')
    )


def downgrade():
    op.drop_table('order')
