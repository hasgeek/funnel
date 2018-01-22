"""state check constraint

Revision ID: cf775ffe502e
Revises: d576f55f9eba
Create Date: 2018-01-02 09:43:02.673275

"""

# revision identifiers, used by Alembic.
revision = 'cf775ffe502e'
down_revision = 'd576f55f9eba'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_check_constraint(
        'ck_proposal_state_valid',
        'proposal',
        'status IN (10, 11, 7, 2, 1, 9, 0, 5, 3, 6, 8, 4)'
    )
    op.create_check_constraint(
        'ck_comment_state_valid',
        'comment',
        'status IN (3, 4, 1, 2, 0)'
    )
    # rsvp status field already has a constraint, dropping it and creating a new one
    op.drop_constraint(
        'rsvp_status_check',
        'rsvp'
    )
    op.create_check_constraint(
        'ck_rsvp_state_valid',
        'rsvp',
        "status IN ('A', 'M', 'N', 'Y')"
    )
    op.create_check_constraint(
        'ck_proposal_space_state_valid',
        'proposal_space',
        'status IN (3, 4, 0, 5, 2, 1, 6)'
    )


def downgrade():
    op.drop_constraint(
        'ck_proposal_state_valid',
        'proposal'
    )
    op.drop_constraint(
        'ck_comment_state_valid',
        'comment'
    )
    op.drop_constraint(
        'ck_rsvp_state_valid',
        'rsvp'
    )
    op.drop_constraint(
        'ck_proposal_space_state_valid',
        'proposal_space'
    )
