"""Added sequence to venue and venue_room.

Revision ID: e417a13e136d
Revises: c3069d33419a
Create Date: 2019-02-07 09:58:40.632722

"""

revision = 'e417a13e136d'
down_revision = 'c3069d33419a'

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import column, table

project = table('project', column('id', sa.Integer()))

venue = table(
    'venue',
    column('id', sa.Integer()),
    column('project_id', sa.Integer()),
    column('seq', sa.Integer()),
    column('created_at', sa.DateTime()),
)

venue_room = table(
    'venue_room',
    column('id', sa.Integer()),
    column('venue_id', sa.Integer()),
    column('seq', sa.Integer()),
    column('created_at', sa.DateTime()),
)


def upgrade() -> None:
    op.add_column('venue', sa.Column('seq', sa.Integer(), nullable=True))
    op.add_column('venue_room', sa.Column('seq', sa.Integer(), nullable=True))

    connection = op.get_bind()

    # update venue sequences
    projects = connection.execute(sa.select(project.c.id))
    project_ids = [proj_tuple[0] for proj_tuple in projects]

    for project_id in project_ids:
        venues = connection.execute(
            sa.select(venue.c.id)
            .where(venue.c.project_id == project_id)
            .order_by('created_at')
        )
        venue_ids = [venue_tuple[0] for venue_tuple in venues]
        for idx, venue_id in enumerate(venue_ids):
            op.execute(
                venue.update().where(venue.c.id == venue_id).values({'seq': idx + 1})
            )

            # update venue_room sequences
            venue_rooms = connection.execute(
                sa.select(venue_room.c.id)
                .where(venue_room.c.venue_id == venue_id)
                .order_by('created_at')
            )
            room_ids = [venue_room_tuple[0] for venue_room_tuple in venue_rooms]

            for idx2, room_id in enumerate(room_ids):
                op.execute(
                    venue_room.update()
                    .where(venue_room.c.id == room_id)
                    .values({'seq': idx2 + 1})
                )

    op.alter_column('venue', 'seq', existing_type=sa.Integer(), nullable=False)
    op.alter_column('venue_room', 'seq', existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    op.drop_column('venue_room', 'seq')
    op.drop_column('venue', 'seq')
