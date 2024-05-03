"""Submission template state.

Revision ID: b24cbe67fdae
Revises: 4eb2369f47f5
Create Date: 2024-05-03 14:18:36.613793

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b24cbe67fdae'
down_revision: str = '4eb2369f47f5'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

proposal = sa.table('proposal', sa.column('state', sa.SmallInteger()))


def upgrade(engine_name: str = '') -> None:
    """Upgrade all databases."""
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name: str = '') -> None:
    """Downgrade all databases."""
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    """Upgrade default database."""
    with op.batch_alter_table('account_membership', schema=None) as batch_op:
        batch_op.alter_column(
            'record_type',
            existing_type=sa.INTEGER(),
            type_=sa.SmallInteger(),
            existing_nullable=False,
        )

    with op.batch_alter_table('comment', schema=None) as batch_op:
        batch_op.alter_column(
            'state',
            existing_type=sa.INTEGER(),
            type_=sa.SmallInteger(),
            existing_nullable=False,
        )

    with op.batch_alter_table('commentset_membership', schema=None) as batch_op:
        batch_op.alter_column(
            'record_type',
            existing_type=sa.INTEGER(),
            type_=sa.SmallInteger(),
            existing_nullable=False,
        )

    with op.batch_alter_table('email_address', schema=None) as batch_op:
        batch_op.alter_column(
            'delivery_state',
            existing_type=sa.INTEGER(),
            type_=sa.SmallInteger(),
            existing_nullable=False,
        )

    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.alter_column(
            'state',
            existing_type=sa.INTEGER(),
            type_=sa.SmallInteger(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            'cfp_state',
            existing_type=sa.INTEGER(),
            type_=sa.SmallInteger(),
            existing_nullable=False,
        )

    with op.batch_alter_table('project_membership', schema=None) as batch_op:
        batch_op.alter_column(
            'record_type',
            existing_type=sa.INTEGER(),
            type_=sa.SmallInteger(),
            existing_nullable=False,
        )

    with op.batch_alter_table('project_sponsor_membership', schema=None) as batch_op:
        batch_op.alter_column(
            'record_type',
            existing_type=sa.INTEGER(),
            type_=sa.SmallInteger(),
            existing_nullable=False,
        )

    with op.batch_alter_table('proposal', schema=None) as batch_op:
        batch_op.alter_column(
            'state',
            existing_type=sa.INTEGER(),
            type_=sa.SmallInteger(),
            existing_nullable=False,
        )
        batch_op.drop_constraint('proposal_state_check', type_='check')
        batch_op.create_check_constraint(
            'proposal_state_check',
            proposal.c.state.in_([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]),
        )

    with op.batch_alter_table('proposal_membership', schema=None) as batch_op:
        batch_op.alter_column(
            'record_type',
            existing_type=sa.INTEGER(),
            type_=sa.SmallInteger(),
            existing_nullable=False,
        )

    with op.batch_alter_table('proposal_sponsor_membership', schema=None) as batch_op:
        batch_op.alter_column(
            'record_type',
            existing_type=sa.INTEGER(),
            type_=sa.SmallInteger(),
            existing_nullable=False,
        )

    with op.batch_alter_table('site_membership', schema=None) as batch_op:
        batch_op.alter_column(
            'record_type',
            existing_type=sa.INTEGER(),
            type_=sa.SmallInteger(),
            existing_nullable=False,
        )


def downgrade_() -> None:
    """Downgrade default database."""
    with op.batch_alter_table('site_membership', schema=None) as batch_op:
        batch_op.alter_column(
            'record_type',
            existing_type=sa.SmallInteger(),
            type_=sa.INTEGER(),
            existing_nullable=False,
        )

    with op.batch_alter_table('proposal_sponsor_membership', schema=None) as batch_op:
        batch_op.alter_column(
            'record_type',
            existing_type=sa.SmallInteger(),
            type_=sa.INTEGER(),
            existing_nullable=False,
        )

    with op.batch_alter_table('proposal_membership', schema=None) as batch_op:
        batch_op.alter_column(
            'record_type',
            existing_type=sa.SmallInteger(),
            type_=sa.INTEGER(),
            existing_nullable=False,
        )

    with op.batch_alter_table('proposal', schema=None) as batch_op:
        batch_op.drop_constraint('proposal_state_check', type_='check')
        batch_op.create_check_constraint(
            'proposal_state_check',
            proposal.c.state.in_([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]),
        )
        batch_op.alter_column(
            'state',
            existing_type=sa.SmallInteger(),
            type_=sa.INTEGER(),
            existing_nullable=False,
        )

    with op.batch_alter_table('project_sponsor_membership', schema=None) as batch_op:
        batch_op.alter_column(
            'record_type',
            existing_type=sa.SmallInteger(),
            type_=sa.INTEGER(),
            existing_nullable=False,
        )

    with op.batch_alter_table('project_membership', schema=None) as batch_op:
        batch_op.alter_column(
            'record_type',
            existing_type=sa.SmallInteger(),
            type_=sa.INTEGER(),
            existing_nullable=False,
        )

    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.alter_column(
            'cfp_state',
            existing_type=sa.SmallInteger(),
            type_=sa.INTEGER(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            'state',
            existing_type=sa.SmallInteger(),
            type_=sa.INTEGER(),
            existing_nullable=False,
        )

    with op.batch_alter_table('email_address', schema=None) as batch_op:
        batch_op.alter_column(
            'delivery_state',
            existing_type=sa.SmallInteger(),
            type_=sa.INTEGER(),
            existing_nullable=False,
        )

    with op.batch_alter_table('commentset_membership', schema=None) as batch_op:
        batch_op.alter_column(
            'record_type',
            existing_type=sa.SmallInteger(),
            type_=sa.INTEGER(),
            existing_nullable=False,
        )

    with op.batch_alter_table('comment', schema=None) as batch_op:
        batch_op.alter_column(
            'state',
            existing_type=sa.SmallInteger(),
            type_=sa.INTEGER(),
            existing_nullable=False,
        )

    with op.batch_alter_table('account_membership', schema=None) as batch_op:
        batch_op.alter_column(
            'record_type',
            existing_type=sa.SmallInteger(),
            type_=sa.INTEGER(),
            existing_nullable=False,
        )
