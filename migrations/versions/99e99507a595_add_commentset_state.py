"""Add commentset state.

Revision ID: 99e99507a595
Revises: 294362dc7e49
Create Date: 2021-08-15 22:43:02.921034

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '99e99507a595'
down_revision = '294362dc7e49'
branch_labels = None
depends_on = None


class COMMENTSET_STATE:
    DISABLED = 1  # Disabled for all
    OPEN = 2  # Open for all
    PARTICIPANTS = 3  # Only for participants
    COLLABORATORS = 4  # Only for editors/collaborators


def upgrade(engine_name=''):
    # Do not modify. Edit `upgrade_` instead
    globals().get('upgrade_%s' % engine_name, lambda: None)()


def downgrade(engine_name=''):
    # Do not modify. Edit `downgrade_` instead
    globals().get('downgrade_%s' % engine_name, lambda: None)()


def upgrade_():
    op.add_column(
        'commentset',
        sa.Column(
            'state',
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text(str(COMMENTSET_STATE.OPEN)),
        ),
    )
    op.alter_column('commentset', 'state', server_default=None)
    op.create_check_constraint(
        'commentset_state_check', 'commentset', 'state IN (1, 2, 3, 4)'
    )


def downgrade_():
    op.drop_constraint('commentset_state_check', 'commentset', type_='check')
    op.drop_column('commentset', 'state')


def upgrade_geoname():
    pass


def downgrade_geoname():
    pass
