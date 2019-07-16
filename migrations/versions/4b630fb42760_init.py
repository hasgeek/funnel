# -*- coding: utf-8 -*-

"""init

Revision ID: 4b630fb42760
Revises: None
Create Date: 2013-08-26 18:05:24.589828

"""

# revision identifiers, used by Alembic.
revision = '4b630fb42760'
down_revision = None

import sqlalchemy as sa  # NOQA
from alembic import op


def upgrade():
    op.create_table(
        'votespace',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('type', sa.Integer(), nullable=True),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'tag',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.Unicode(length=80), nullable=False),
        sa.Column('title', sa.Unicode(length=80), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('title'),
    )
    op.create_table(
        'commentspace',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('type', sa.Integer(), nullable=True),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('username', sa.Unicode(length=80), nullable=True),
        sa.Column('lastuser_token_scope', sa.Unicode(length=250), nullable=True),
        sa.Column('userinfo', sa.UnicodeText(), nullable=True),
        sa.Column('lastuser_token_type', sa.Unicode(length=250), nullable=True),
        sa.Column('userid', sa.String(length=22), nullable=False),
        sa.Column('lastuser_token', sa.String(length=22), nullable=True),
        sa.Column('fullname', sa.Unicode(length=80), nullable=False),
        sa.Column('email', sa.Unicode(length=80), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('lastuser_token'),
        sa.UniqueConstraint('userid'),
        sa.UniqueConstraint('username'),
    )
    op.create_table(
        'vote',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('votespace_id', sa.Integer(), nullable=False),
        sa.Column('votedown', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['votespace_id'], ['votespace.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'votespace_id'),
    )
    op.create_table(
        'comment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('commentspace_id', sa.Integer(), nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('message_html', sa.Text(), nullable=False),
        sa.Column('status', sa.Integer(), nullable=False),
        sa.Column('votes_id', sa.Integer(), nullable=False),
        sa.Column('edited_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['commentspace_id'], ['commentspace.id']),
        sa.ForeignKeyConstraint(['parent_id'], ['comment.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['votes_id'], ['votespace.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'proposal_space',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Unicode(length=80), nullable=False),
        sa.Column('title', sa.Unicode(length=80), nullable=False),
        sa.Column('tagline', sa.Unicode(length=250), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('description_html', sa.Text(), nullable=False),
        sa.Column('datelocation', sa.Unicode(length=50), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('website', sa.Unicode(length=250), nullable=True),
        sa.Column('status', sa.Integer(), nullable=False),
        sa.Column('votes_id', sa.Integer(), nullable=False),
        sa.Column('comments_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['comments_id'], ['commentspace.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['votes_id'], ['votespace.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_table(
        'user_group',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.Unicode(length=250), nullable=False),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.Column('proposal_space_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['proposal_space_id'], ['proposal_space.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'proposal_space_section',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('proposal_space_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Unicode(length=80), nullable=False),
        sa.Column('title', sa.Unicode(length=80), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('public', sa.Boolean(), nullable=False),
        sa.Column('votes_id', sa.Integer(), nullable=False),
        sa.Column('comments_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['comments_id'], ['commentspace.id']),
        sa.ForeignKeyConstraint(['proposal_space_id'], ['proposal_space.id']),
        sa.ForeignKeyConstraint(['votes_id'], ['votespace.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('proposal_space_id', 'name'),
    )
    op.create_table(
        'group_members',
        sa.Column('group_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['user_group.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint(),
    )
    op.create_table(
        'proposal',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('speaker_id', sa.Integer(), nullable=True),
        sa.Column('email', sa.Unicode(length=80), nullable=True),
        sa.Column('phone', sa.Unicode(length=80), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('bio_html', sa.Text(), nullable=True),
        sa.Column('proposal_space_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Unicode(length=250), nullable=False),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.Column('section_id', sa.Integer(), nullable=True),
        sa.Column('objective', sa.Text(), nullable=False),
        sa.Column('objective_html', sa.Text(), nullable=False),
        sa.Column('session_type', sa.Unicode(length=40), nullable=False),
        sa.Column('technical_level', sa.Unicode(length=40), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('description_html', sa.Text(), nullable=False),
        sa.Column('requirements', sa.Text(), nullable=False),
        sa.Column('requirements_html', sa.Text(), nullable=False),
        sa.Column('slides', sa.Unicode(length=250), nullable=False),
        sa.Column('links', sa.Text(), nullable=False),
        sa.Column('status', sa.Integer(), nullable=False),
        sa.Column('confirmed', sa.Boolean(), nullable=False),
        sa.Column('votes_id', sa.Integer(), nullable=False),
        sa.Column('comments_id', sa.Integer(), nullable=False),
        sa.Column('edited_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['comments_id'], ['commentspace.id']),
        sa.ForeignKeyConstraint(['proposal_space_id'], ['proposal_space.id']),
        sa.ForeignKeyConstraint(['section_id'], ['proposal_space_section.id']),
        sa.ForeignKeyConstraint(['speaker_id'], ['user.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['votes_id'], ['votespace.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'proposal_tags',
        sa.Column('tag_id', sa.Integer(), nullable=True),
        sa.Column('proposal_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposal.id']),
        sa.ForeignKeyConstraint(['tag_id'], ['tag.id']),
        sa.PrimaryKeyConstraint(),
    )


def downgrade():
    op.drop_table('proposal_tags')
    op.drop_table('proposal')
    op.drop_table('group_members')
    op.drop_table('proposal_space_section')
    op.drop_table('user_group')
    op.drop_table('proposal_space')
    op.drop_table('comment')
    op.drop_table('vote')
    op.drop_table('user')
    op.drop_table('commentspace')
    op.drop_table('tag')
    op.drop_table('votespace')
