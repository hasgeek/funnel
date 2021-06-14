"""Remove voteset and vote.

Revision ID: 896137ace892
Revises: 6835596b1eee
Create Date: 2021-06-15 03:26:20.618000

"""

from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '896137ace892'
down_revision = '6835596b1eee'
branch_labels = None
depends_on = None


def upgrade(engine_name=''):
    # Do not modify. Edit `upgrade_` instead
    globals().get('upgrade_%s' % engine_name, lambda: None)()


def downgrade(engine_name=''):
    # Do not modify. Edit `downgrade_` instead
    globals().get('downgrade_%s' % engine_name, lambda: None)()


def upgrade_():
    op.drop_constraint('comment_voteset_id_fkey', 'comment', type_='foreignkey')
    op.drop_column('comment', 'voteset_id')
    op.drop_constraint('project_voteset_id_fkey', 'project', type_='foreignkey')
    op.drop_column('project', 'voteset_id')
    op.drop_constraint('proposal_voteset_id_fkey', 'proposal', type_='foreignkey')
    op.drop_column('proposal', 'voteset_id')
    op.drop_constraint('update_voteset_id_fkey', 'update', type_='foreignkey')
    op.drop_column('update', 'voteset_id')
    op.drop_index('ix_vote_user_id', table_name='vote')
    op.drop_table('vote')
    op.drop_table('voteset')


def downgrade_():
    op.create_table(
        'voteset',
        sa.Column(
            'id',
            sa.INTEGER(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            'created_at',
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column('type', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('count', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint('id', name='voteset_pkey'),
        postgresql_ignore_search_path=False,
    )
    op.create_table(
        'vote',
        sa.Column(
            'created_at',
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column('voteset_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('votedown', sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], name='vote_user_id_fkey'),
        sa.ForeignKeyConstraint(
            ['voteset_id'], ['voteset.id'], name='vote_voteset_id_fkey'
        ),
        sa.PrimaryKeyConstraint('voteset_id', 'user_id', name='vote_pkey'),
    )
    op.create_index('ix_vote_user_id', 'vote', ['user_id'], unique=False)

    # XXX: These columns were originally nullable=False, but this downgrade can't
    # restore vote data, so it doesn't bother to create empty votesets for all existing
    # content
    op.add_column(
        'update',
        sa.Column('voteset_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        'update_voteset_id_fkey', 'update', 'voteset', ['voteset_id'], ['id']
    )
    op.add_column(
        'proposal',
        sa.Column('voteset_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        'proposal_voteset_id_fkey', 'proposal', 'voteset', ['voteset_id'], ['id']
    )
    op.add_column(
        'project',
        sa.Column('voteset_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        'project_voteset_id_fkey', 'project', 'voteset', ['voteset_id'], ['id']
    )
    op.add_column(
        'comment',
        sa.Column('voteset_id', sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        'comment_voteset_id_fkey', 'comment', 'voteset', ['voteset_id'], ['id']
    )
