"""Profiles and UserBase2.

Revision ID: 1bb2df0df8e2
Revises: 523c53593e3c
Create Date: 2014-04-06 18:49:43.418238

"""

# revision identifiers, used by Alembic.
revision = '1bb2df0df8e2'
down_revision = '523c53593e3c'

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        'user',
        sa.Column('status', sa.Integer(), nullable=False, server_default=sa.text('0')),
    )
    op.alter_column('user', 'status', server_default=None)

    op.create_table(
        'profile',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('description_text', sa.UnicodeText(), nullable=False),
        sa.Column('description_html', sa.UnicodeText(), nullable=False),
        sa.Column('status', sa.Integer(), nullable=False),
        sa.Column('userid', sa.Unicode(length=22), nullable=False),
        sa.Column('name', sa.Unicode(length=250), nullable=False),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('userid'),
    )

    op.add_column(
        'proposal_space', sa.Column('profile_id', sa.Integer(), nullable=True)
    )
    op.drop_constraint('proposal_space_name_key', 'proposal_space')
    op.create_unique_constraint(
        'proposal_space_profile_id_name_key', 'proposal_space', ['profile_id', 'name']
    )


def downgrade() -> None:
    op.drop_constraint('proposal_space_profile_id_name_key', 'proposal_space')
    op.create_unique_constraint('proposal_space_name_key', 'proposal_space', ['name'])
    op.drop_column('proposal_space', 'profile_id')

    op.drop_table('profile')
    op.drop_column('user', 'status')
