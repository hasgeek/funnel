# -*- coding: utf-8 -*-

"""add labels

# Revision ID: 0b25df40d307
# Revises: ef93d256a8cf
Create Date: 2019-04-08 14:44:05.164533

"""

# revision identifiers, used by Alembic.
revision = '0b25df40d307'
down_revision = 'ef93d256a8cf'

import sqlalchemy as sa
from alembic import op


def upgrade():
    op.create_table(
        'label',
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('main_label_id', sa.Integer(), nullable=True),
        sa.Column('seq', sa.Integer(), nullable=False),
        sa.Column('description', sa.UnicodeText(), nullable=False),
        sa.Column('icon_emoji', sa.UnicodeText(), nullable=True),
        sa.Column('archived', sa.Boolean(), nullable=False),
        sa.Column('restricted', sa.Boolean(), nullable=False),
        sa.Column('required', sa.Boolean(), nullable=False),
        sa.Column('name', sa.Unicode(length=250), nullable=False),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['main_label_id'], ['label.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'name'),
    )
    op.create_table(
        'proposal_label',
        sa.Column('proposal_id', sa.Integer(), nullable=False),
        sa.Column('label_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['label_id'], ['label.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposal.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('proposal_id', 'label_id'),
    )
    op.create_index(
        op.f('ix_proposal_label_label_id'), 'proposal_label', ['label_id'], unique=False
    )


def downgrade():
    op.drop_index(op.f('ix_proposal_label_label_id'), table_name='proposal_label')
    op.drop_table('proposal_label')
    op.drop_table('label')
