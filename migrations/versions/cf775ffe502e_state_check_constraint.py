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
from funnel.models.proposal import PROPOSALSTATUS
from funnel.models.commentvote import COMMENTSTATUS
from funnel.models.rsvp import RSVP_STATUS
from funnel.models.space import SPACESTATUS
from sqlalchemy.sql import column


def upgrade():
    op.create_check_constraint(
        'ck_proposal_state_valid',
        'proposal',
        column('status').in_(PROPOSALSTATUS.keys())
    )
    op.create_check_constraint(
        'ck_comment_state_valid',
        'comment',
        column('status').in_(COMMENTSTATUS.keys())
    )
    # rsvp status field already has a constraint, dropping it and creating a new one
    op.drop_constraint(
        'rsvp_status_check',
        'rsvp'
    )
    op.create_check_constraint(
        'ck_rsvp_state_valid',
        'rsvp',
        column('status').in_(RSVP_STATUS.keys())
    )
    op.create_check_constraint(
        'ck_proposal_space_state_valid',
        'proposal_space',
        column('status').in_(SPACESTATUS.keys())
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
