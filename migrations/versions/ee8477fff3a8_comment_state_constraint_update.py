"""Comment.state constraint update.

Revision ID: ee8477fff3a8
Revises: d5d6aba41475
Create Date: 2021-05-13 11:22:48.033582

"""

from typing import Optional, Tuple, Union

from alembic import op

# revision identifiers, used by Alembic.
revision = 'ee8477fff3a8'
down_revision = '061eefe61519'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade() -> None:
    op.drop_constraint('comment_state_check', 'comment', type_='check')
    op.create_check_constraint(
        'comment_state_check', 'comment', 'state IN (0, 1, 2, 3, 4, 5)'
    )


def downgrade() -> None:
    op.drop_constraint('comment_state_check', 'comment', type_='check')
    op.create_check_constraint(
        'comment_state_check', 'comment', 'state IN (0, 1, 2, 3, 4)'
    )
