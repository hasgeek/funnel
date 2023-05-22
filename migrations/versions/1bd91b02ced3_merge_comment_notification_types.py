"""Merge comment notification types.

Revision ID: 1bd91b02ced3
Revises: 4845fd12dbfd
Create Date: 2020-09-18 02:44:20.827703

"""

from typing import Optional, Tuple, Union

from alembic import op
from sqlalchemy.sql import column, table
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1bd91b02ced3'
down_revision = '4845fd12dbfd'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


notification = table(
    'notification',
    column('eventid', sa.Uuid()),
    column('id', sa.Uuid()),
    column('type', sa.Unicode()),
    column('document_uuid', sa.Uuid()),
    column('fragment_uuid', sa.Uuid()),
)

project = table(
    'project',
    column('id', sa.Integer()),
    column('uuid', sa.Uuid()),
    column('commentset_id', sa.Integer()),
)

proposal = table(
    'proposal',
    column('id', sa.Integer()),
    column('uuid', sa.Uuid()),
    column('commentset_id', sa.Integer()),
)

commentset = table(
    'commentset',
    column('id', sa.Integer()),
    column('uuid', sa.Uuid()),
)


def upgrade():
    # UPDATE notification SET type=:type, document_uuid=commentset.uuid
    # FROM project, commentset
    # WHERE notification.type = :type_1 AND notification.document_uuid = project.uuid
    # AND project.commentset_id = commentset.id
    op.execute(
        notification.update()
        .values(type='comment_new', document_uuid=commentset.c.uuid)
        .where(notification.c.type == 'comment_project')
        .where(notification.c.document_uuid == project.c.uuid)
        .where(project.c.commentset_id == commentset.c.id)
    )

    op.execute(
        notification.update()
        .values(type='comment_new', document_uuid=commentset.c.uuid)
        .where(notification.c.type == 'comment_proposal')
        .where(notification.c.document_uuid == proposal.c.uuid)
        .where(proposal.c.commentset_id == commentset.c.id)
    )


def downgrade():
    op.execute(
        notification.update()
        .values(type='comment_proposal', document_uuid=proposal.c.uuid)
        .where(notification.c.type == 'comment_new')
        .where(notification.c.document_uuid == commentset.c.uuid)
        .where(proposal.c.commentset_id == commentset.c.id)
    )

    op.execute(
        notification.update()
        .values(type='comment_project', document_uuid=project.c.uuid)
        .where(notification.c.type == 'comment_new')
        .where(notification.c.document_uuid == commentset.c.uuid)
        .where(project.c.commentset_id == commentset.c.id)
    )
