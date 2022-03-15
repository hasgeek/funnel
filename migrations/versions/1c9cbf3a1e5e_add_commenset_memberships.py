"""Add commentset memberships.

Revision ID: 1c9cbf3a1e5e
Revises: 7d5b77aada1e
Create Date: 2021-03-11 09:07:56.611054

"""

from uuid import uuid4

from alembic import op
from sqlalchemy.sql import column, table
from sqlalchemy_utils import UUIDType
import sqlalchemy as sa

from progressbar import ProgressBar
import progressbar.widgets

# revision identifiers, used by Alembic.
revision = '1c9cbf3a1e5e'
down_revision = '7d5b77aada1e'
branch_labels = None
depends_on = None


project = table(
    'project',
    column('id', sa.Integer()),
    column('commentset_id', sa.Integer()),
)


rsvp = table(
    'rsvp',
    column('project_id', sa.Integer()),
    column('user_id', sa.Integer()),
    column('state', sa.CHAR(1)),
    column('created_at', sa.TIMESTAMP(timezone=True)),
)


commentset = table(
    'commentset',
    column('id', sa.Integer()),
    column('uuid', UUIDType(binary=False)),
    column('type', sa.Integer()),
    column('count', sa.Integer()),
)


proposal = table(
    'proposal',
    column('id', sa.Integer()),
    column('uuid', UUIDType(binary=False)),
    column('user_id', sa.Integer()),
    column('commentset_id', sa.Integer()),
)


commentset_membership = table(
    'commentset_membership',
    column('id', UUIDType(binary=False)),
    column('user_id', sa.Integer()),
    column('commentset_id', sa.Integer()),
    column('record_type', sa.Integer()),
    column('granted_by_id', sa.Integer()),
    column('granted_at', sa.TIMESTAMP(timezone=True)),
    column('is_muted', sa.TIMESTAMP(timezone=True)),
    column('last_seen_at', sa.TIMESTAMP(timezone=True)),
    column('revoked_at', sa.TIMESTAMP(timezone=True)),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('updated_at', sa.TIMESTAMP(timezone=True)),
)


project_crew_membership = table(
    'project_crew_membership',
    column('id', UUIDType(binary=False)),
    column('user_id', sa.Integer()),
    column('project_id', sa.Integer()),
    column('granted_at', sa.TIMESTAMP(timezone=True)),
    column('revoked_at', sa.TIMESTAMP(timezone=True)),
)


proposal_membership = table(
    'proposal_membership',
    column('id', UUIDType(binary=False)),
    column('user_id', sa.Integer()),
    column('proposal_id', sa.Integer()),
    column('granted_at', sa.TIMESTAMP(timezone=True)),
    column('revoked_at', sa.TIMESTAMP(timezone=True)),
)


class MEMBERSHIP_RECORD_TYPE:
    """Membership record types."""

    INVITE = 0
    ACCEPT = 1
    DIRECT_ADD = 2
    AMEND = 3


def get_progressbar(label, maxval):
    return ProgressBar(
        maxval=maxval,
        widgets=[
            label,
            ': ',
            progressbar.widgets.Percentage(),
            ' ',
            progressbar.widgets.Bar(),
            ' ',
            progressbar.widgets.ETA(),
            ' ',
        ],
    )


def upgrade(engine_name=''):
    # Do not modify. Edit `upgrade_` instead
    globals().get('upgrade_%s' % engine_name, lambda: None)()


def downgrade(engine_name=''):
    # Do not modify. Edit `downgrade_` instead
    globals().get('downgrade_%s' % engine_name, lambda: None)()


def upgrade_():
    conn = op.get_bind()

    count = conn.scalar(sa.select([sa.func.count('*')]).select_from(project))
    progress = get_progressbar("Projects", count)
    progress.start()

    projects = conn.execute(
        sa.select([project.c.id, project.c.commentset_id]).order_by(project.c.id.desc())
    )
    for counter, project_item in enumerate(projects):
        # Create membership for existing RSVP
        rsvp_count = conn.scalar(
            sa.select([sa.func.count('*')])
            .where(rsvp.c.project_id == project_item.id)
            .select_from(rsvp)
        )
        if rsvp_count == 0:
            continue

        rsvps = conn.execute(
            sa.select(
                [rsvp.c.project_id, rsvp.c.user_id, rsvp.c.state, rsvp.c.created_at]
            )
            .where(rsvp.c.project_id == project_item.id)
            .where(rsvp.c.state == 'Y')
            .select_from(rsvp)
        )

        for rsvp_item in rsvps:
            existing_counter = conn.scalar(
                sa.select([sa.func.count('*')])
                .where(
                    commentset_membership.c.commentset_id == project_item.commentset_id
                )
                .where(commentset_membership.c.user_id == rsvp_item.user_id)
                .where(commentset_membership.c.revoked_at.is_(None))
                .select_from(commentset_membership)
            )
            if existing_counter == 0:
                conn.execute(
                    commentset_membership.insert().values(
                        {
                            'id': uuid4(),
                            'user_id': rsvp_item.user_id,
                            'commentset_id': project_item.commentset_id,
                            'record_type': MEMBERSHIP_RECORD_TYPE.DIRECT_ADD,
                            'granted_by_id': rsvp_item.user_id,  # because user registered
                            'granted_at': rsvp_item.created_at,
                            'created_at': sa.func.utcnow(),
                            'updated_at': sa.func.utcnow(),
                            'is_muted': sa.sql.expression.false(),
                            'last_seen_at': sa.func.utcnow(),
                        }
                    )
                )

        # Create membership for existing project crew
        crews = conn.execute(
            sa.select(
                [
                    project_crew_membership.c.user_id,
                    project_crew_membership.c.granted_at,
                ]
            )
            .where(project_crew_membership.c.project_id == project_item.id)
            .where(project_crew_membership.c.revoked_at.is_(None))
            .select_from(project_crew_membership)
        )

        for crew in crews:
            existing_counter = conn.scalar(
                sa.select([sa.func.count('*')])
                .where(
                    commentset_membership.c.commentset_id == project_item.commentset_id
                )
                .where(commentset_membership.c.user_id == crew.user_id)
                .where(commentset_membership.c.revoked_at.is_(None))
                .select_from(commentset_membership)
            )
            if existing_counter == 0:
                conn.execute(
                    commentset_membership.insert().values(
                        {
                            'id': uuid4(),
                            'user_id': crew.user_id,
                            'commentset_id': project_item.commentset_id,
                            'record_type': MEMBERSHIP_RECORD_TYPE.DIRECT_ADD,
                            'granted_by_id': crew.user_id,
                            'granted_at': crew.granted_at,
                            'created_at': sa.func.utcnow(),
                            'updated_at': sa.func.utcnow(),
                            'is_muted': sa.sql.expression.false(),
                            'last_seen_at': sa.func.utcnow(),
                        }
                    )
                )
        progress.update(counter)
    progress.finish()

    # Create commentset membership for existing proposal memberships
    count = conn.scalar(
        sa.select([sa.func.count('*')]).select_from(proposal_membership)
    )
    progress = get_progressbar("Proposals", count)
    progress.start()

    proposals = conn.execute(
        sa.select(
            [
                proposal.c.id,
                proposal.c.commentset_id,
                proposal_membership.c.user_id,
                proposal_membership.c.granted_at,
            ]
        )
        .where(proposal_membership.c.proposal_id == proposal.c.id)
        .where(proposal_membership.c.revoked_at.is_(None))
        .select_from(proposal_membership, proposal)
        .order_by(proposal.c.id.desc())
    )
    for counter, proposal_item in enumerate(proposals):
        existing_counter = conn.scalar(
            sa.select([sa.func.count('*')])
            .where(commentset_membership.c.commentset_id == proposal_item.commentset_id)
            .where(commentset_membership.c.user_id == proposal_item.user_id)
            .where(commentset_membership.c.revoked_at.is_(None))
            .select_from(commentset_membership)
        )
        if existing_counter == 0:
            conn.execute(
                commentset_membership.insert().values(
                    {
                        'id': uuid4(),
                        'user_id': proposal_item.user_id,
                        'commentset_id': proposal_item.commentset_id,
                        'record_type': MEMBERSHIP_RECORD_TYPE.DIRECT_ADD,
                        'granted_by_id': proposal_item.user_id,
                        'granted_at': proposal_item.granted_at,
                        'created_at': sa.func.utcnow(),
                        'updated_at': sa.func.utcnow(),
                        'is_muted': sa.sql.expression.false(),
                        'last_seen_at': sa.func.utcnow(),
                    }
                )
            )
        progress.update(counter)
    progress.finish()


def downgrade_():
    conn = op.get_bind()

    count = conn.scalar(sa.select([sa.func.count('*')]).select_from(project))
    progress = get_progressbar("Projects", count)
    progress.start()

    projects = conn.execute(sa.select([project.c.id, project.c.commentset_id]))
    for counter, project_item in enumerate(projects):
        commentset_memberships = conn.execute(
            sa.select([commentset_membership.c.id])
            .where(commentset_membership.c.commentset_id == project_item.commentset_id)
            .where(commentset_membership.c.revoked_at is None)
            .select_from(commentset_membership)
        )
        for membership_item in commentset_memberships:
            conn.execute(
                sa.delete(commentset_membership).where(
                    commentset_membership.c.id == membership_item.id
                )
            )
        progress.update(counter)
    progress.finish()

    count = conn.scalar(sa.select([sa.func.count('*')]).select_from(proposal))
    progress = get_progressbar("Proposals", count)
    progress.start()

    proposals = conn.execute(
        sa.select([proposal.c.id, proposal.c.commentset_id]).order_by(
            proposal.c.id.desc()
        )
    )
    for counter, proposal_item in enumerate(proposals):
        commentset_memberships = conn.execute(
            sa.select([commentset_membership.c.id])
            .where(commentset_membership.c.commentset_id == proposal_item.commentset_id)
            .where(commentset_membership.c.revoked_at is None)
            .select_from(commentset_membership)
        )
        for membership_item in commentset_memberships:
            conn.execute(
                sa.delete(commentset_membership).where(
                    commentset_membership.c.id == membership_item.id
                )
            )
        progress.update(counter)
    progress.finish()
