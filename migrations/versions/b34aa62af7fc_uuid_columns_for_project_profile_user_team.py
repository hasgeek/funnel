"""UUID columns for Project, Profile, User, Team

Revision ID: b34aa62af7fc
Revises: 19a1f7f2a365
Create Date: 2018-12-06 20:38:40.092866

"""

# revision identifiers, used by Alembic.
revision = 'b34aa62af7fc'
down_revision = '19a1f7f2a365'

from uuid import uuid4

import sqlalchemy as sa  # NOQA
from alembic import op
from sqlalchemy.sql import column, table
from sqlalchemy_utils import UUIDType

import progressbar.widgets
from progressbar import ProgressBar

from coaster.utils import buid2uuid, uuid2buid

project = table('project',
    column('id', sa.Integer()),
    column('uuid', UUIDType(binary=False)),
    )

profile = table('profile',
    column('id', sa.Integer()),
    column('uuid', UUIDType(binary=False)),
    column('userid', sa.String(22)),
    )

user = table('user',
    column('id', sa.Integer()),
    column('uuid', UUIDType(binary=False)),
    column('userid', sa.String(22)),
    )

team = table('team',
    column('id', sa.Integer()),
    column('uuid', UUIDType(binary=False)),
    column('userid', sa.String(22)),
    )


def get_progressbar(label, maxval):
    return ProgressBar(
        maxval=maxval,
        widgets=[
            label, ': ',
            progressbar.widgets.Percentage(), ' ',
            progressbar.widgets.Bar(), ' ',
            progressbar.widgets.ETA(), ' '
            ])


def upgrade():
    conn = op.get_bind()

    # --- Project
    op.add_column('project', sa.Column('uuid', UUIDType(binary=False), nullable=True))
    count = conn.scalar(
        sa.select([sa.func.count('*')]).select_from(project))
    progress = get_progressbar("Projects", count)
    progress.start()
    items = conn.execute(sa.select([project.c.id]))
    for counter, item in enumerate(items):
        conn.execute(sa.update(project).where(project.c.id == item.id).values(uuid=uuid4()))
        progress.update(counter)
    progress.finish()
    op.alter_column('project', 'uuid', nullable=False)
    op.create_unique_constraint('project_uuid_key', 'project', ['uuid'])

    # --- Profile
    op.add_column('profile', sa.Column('uuid', UUIDType(binary=False), nullable=True))
    count = conn.scalar(
        sa.select([sa.func.count('*')]).select_from(profile))
    progress = get_progressbar("Profiles", count)
    progress.start()
    items = conn.execute(sa.select([profile.c.id, profile.c.userid]))
    for counter, item in enumerate(items):
        conn.execute(sa.update(profile).where(profile.c.id == item.id).values(uuid=buid2uuid(item.userid)))
        progress.update(counter)
    progress.finish()
    op.alter_column('profile', 'uuid', nullable=False)
    op.create_unique_constraint('profile_uuid_key', 'profile', ['uuid'])
    op.drop_constraint('profile_userid_key', 'profile', type_='unique')
    op.drop_column('profile', 'userid')

    # --- Team
    op.add_column('team', sa.Column('uuid', UUIDType(binary=False), nullable=True))
    count = conn.scalar(
        sa.select([sa.func.count('*')]).select_from(team))
    progress = get_progressbar("Teams", count)
    progress.start()
    items = conn.execute(sa.select([team.c.id, team.c.userid]))
    for counter, item in enumerate(items):
        conn.execute(sa.update(team).where(team.c.id == item.id).values(uuid=buid2uuid(item.userid)))
        progress.update(counter)
    progress.finish()
    op.alter_column('team', 'uuid', nullable=False)
    op.create_unique_constraint('team_uuid_key', 'team', ['uuid'])
    op.drop_constraint('team_userid_key', 'team', type_='unique')
    op.drop_column('team', 'userid')

    # --- User
    op.add_column('user', sa.Column('uuid', UUIDType(binary=False), nullable=True))
    count = conn.scalar(
        sa.select([sa.func.count('*')]).select_from(user))
    progress = get_progressbar("Users", count)
    progress.start()
    items = conn.execute(sa.select([user.c.id, user.c.userid]))
    for counter, item in enumerate(items):
        conn.execute(sa.update(user).where(user.c.id == item.id).values(uuid=buid2uuid(item.userid)))
        progress.update(counter)
    progress.finish()
    op.alter_column('user', 'uuid', nullable=False)
    op.create_unique_constraint('user_uuid_key', 'user', ['uuid'])
    op.drop_constraint('user_userid_key', 'user', type_='unique')
    op.drop_column('user', 'userid')


def downgrade():
    conn = op.get_bind()

    # --- User
    op.add_column('user', sa.Column('userid', sa.String(22), nullable=True))
    op.create_unique_constraint('user_userid_key', 'user', ['userid'])
    count = conn.scalar(
        sa.select([sa.func.count('*')]).select_from(user))
    progress = get_progressbar("Users", count)
    progress.start()
    items = conn.execute(sa.select([user.c.id, user.c.uuid]))
    for counter, item in enumerate(items):
        conn.execute(sa.update(user).where(user.c.id == item.id).values(userid=uuid2buid(item.uuid)))
        progress.update(counter)
    progress.finish()
    op.alter_column('user', 'userid', nullable=False)
    op.drop_constraint('user_uuid_key', 'user', type_='unique')
    op.drop_column('user', 'uuid')

    # --- Team
    op.add_column('team', sa.Column('userid', sa.String(22), nullable=True))
    op.create_unique_constraint('team_userid_key', 'team', ['userid'])
    count = conn.scalar(
        sa.select([sa.func.count('*')]).select_from(team))
    progress = get_progressbar("Teams", count)
    progress.start()
    items = conn.execute(sa.select([team.c.id, team.c.uuid]))
    for counter, item in enumerate(items):
        conn.execute(sa.update(team).where(team.c.id == item.id).values(userid=uuid2buid(item.uuid)))
        progress.update(counter)
    progress.finish()
    op.alter_column('team', 'userid', nullable=False)
    op.drop_constraint('team_uuid_key', 'team', type_='unique')
    op.drop_column('team', 'uuid')

    # --- Profile
    op.add_column('profile', sa.Column('userid', sa.String(22), nullable=True))
    op.create_unique_constraint('profile_userid_key', 'profile', ['userid'])
    count = conn.scalar(
        sa.select([sa.func.count('*')]).select_from(profile))
    progress = get_progressbar("Profiles", count)
    progress.start()
    items = conn.execute(sa.select([profile.c.id, profile.c.uuid]))
    for counter, item in enumerate(items):
        conn.execute(sa.update(profile).where(profile.c.id == item.id).values(userid=uuid2buid(item.uuid)))
        progress.update(counter)
    progress.finish()
    op.alter_column('profile', 'userid', nullable=False)
    op.drop_constraint('profile_uuid_key', 'profile', type_='unique')
    op.drop_column('profile', 'uuid')

    # --- Project
    op.drop_constraint('project_uuid_key', 'project', type_='unique')
    op.drop_column('project', 'uuid')
