# type: ignore
"""Change Vote table to use composite pkey.

Revision ID: 6ebbe0cc8e19
Revises: 7ee3c83f713f
Create Date: 2020-05-05 00:48:41.032308

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.schema import CreateSequence, Sequence

# revision identifiers, used by Alembic.
revision = '6ebbe0cc8e19'
down_revision = '7ee3c83f713f'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_index(op.f('ix_vote_user_id'), 'vote', ['user_id'], unique=False)
    op.drop_constraint('vote_user_id_voteset_id_key', 'vote', type_='unique')
    op.drop_constraint('vote_pkey', 'vote', type_='primary')
    op.drop_column('vote', 'id')
    op.create_primary_key('vote_pkey', 'vote', ['voteset_id', 'user_id'])


def downgrade() -> None:
    op.drop_constraint('vote_pkey', 'vote', type_='primary')
    op.execute(CreateSequence(Sequence('vote_id_seq')))
    op.add_column(
        'vote',
        sa.Column(
            'id',
            sa.INTEGER(),
            nullable=False,
            server_default=sa.text("nextval('vote_id_seq'::regclass)"),
        ),
    )
    op.create_primary_key('vote_pkey', 'vote', ['id'])
    op.create_unique_constraint(
        'vote_user_id_voteset_id_key', 'vote', ['user_id', 'voteset_id']
    )
    op.drop_index(op.f('ix_vote_user_id'), table_name='vote')
