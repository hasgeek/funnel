"""migrate old labels

Revision ID: f89e3a85ed10
Revises: 0b25df40d307
Create Date: 2019-04-11 14:42:55.182622

"""

# revision identifiers, used by Alembic.
revision = 'f89e3a85ed10'
down_revision = '0b25df40d307'

from datetime import datetime
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


proposal = table('proposal',
    column('id', sa.Integer()),
    column('project_id', sa.Integer()),
    column('technical_level', sa.Unicode(40)),
    column('session_type', sa.Unicode(40)),
    column('section_id', sa.Integer()),
    )

project = table('project',
    column('id', sa.Integer()),
    column('name', sa.Unicode(250))
    )

section = table('section',
    column('id', sa.Integer()),
    column('project_id', sa.Integer()),
    column('name', sa.Unicode(250)),
    column('title', sa.Unicode(250)),
    column('description', sa.UnicodeText()),
    column('created_at', sa.DateTime()),
    column('updated_at', sa.DateTime())
    )

labelset = table('labelset',
    column('id', sa.Integer()),
    column('name', sa.Unicode(250)),
    column('title', sa.Unicode(250)),
    column('project_id', sa.Integer()),
    column('seq', sa.Integer()),
    column('description', sa.UnicodeText()),
    column('radio_mode', sa.Boolean()),
    column('restricted', sa.Boolean()),
    column('required', sa.Boolean()),
    column('created_at', sa.DateTime()),
    column('updated_at', sa.DateTime())
    )

label = table('label',
    column('id', sa.Integer()),
    column('name', sa.Unicode(250)),
    column('title', sa.Unicode(250)),
    column('bgcolor', sa.Unicode(6)),
    column('labelset_id', sa.Integer()),
    column('seq', sa.Integer()),
    column('created_at', sa.DateTime()),
    column('updated_at', sa.DateTime())
    )

proposal_label = table('proposal_label',
    column('proposal_id', sa.Integer()),
    column('label_id', sa.Integer()),
    column('created_at', sa.DateTime())
    )


def upgrade():
    conn = op.get_bind()
    # Migrate sections -
    projects = conn.execute(project.select())
    for proj in projects:
        sec_count = conn.scalar(
                sa.select([sa.func.count('*')]).select_from(section).where(section.c.project_id == proj['id'])
            )
        if sec_count > 0:
            # the project has some sections
            # create section labelset for the project
            labset = conn.execute(labelset.insert().values({
                    'project_id': proj['id'], 'name': u"section", 'title': u"Section",
                    'seq': 1, 'description': "", 'radio_mode': True, 'restricted': True,
                    'required': True, 'created_at': datetime.now(), 'updated_at': datetime.now()
                }).returning(labelset.c.id)).first()

            # add old sections as labels to the above labelset
            sections = conn.execute(section.select().where(section.c.project_id == proj['id']))
            for index, sec in enumerate(sections, start=1):
                lab = conn.execute(label.insert().values({
                    'name': sec['name'], 'title': sec['title'],
                    'labelset_id': labset[0], 'seq': index, 'bgcolor': u"CCCCCC",
                    'created_at': datetime.now(), 'updated_at': datetime.now()
                }).returning(label.c.id, label.c.name)).first()

                # only select proposals that belonged to above section and
                # still in the same project as the section. This removed proposals
                # that were moved to other projects but their section relationship
                # was never migrated.
                proposals = conn.execute(
                        proposal.select().where(proposal.c.section_id == sec['id']).where(proposal.c.project_id == sec['project_id'])
                    )
                for prop in proposals:
                    pl = conn.execute(proposal_label.insert().values({
                        'proposal_id': prop['id'], 'label_id': lab['id'], 'created_at': datetime.now()
                    }))

        # technical level
        labset = conn.execute(labelset.insert().values({
            'project_id': proj['id'], 'name': u"technical-level", 'title': u"Technical Level",
            'seq': 1, 'description': "", 'radio_mode': True, 'restricted': True,
            'required': True, 'created_at': datetime.now(), 'updated_at': datetime.now()
        }).returning(labelset.c.id)).first()
        tl_list = [('beginner', "Beginner"), ('intermediate', "Intermediate"), ('advanced', "Advanced")]
        for index, tl in enumerate(tl_list):
            tl_name, tl_title = tl
            lab = conn.execute(label.insert().values({
                    'name': tl_name, 'title': tl_title,
                    'labelset_id': labset[0], 'seq': index, 'bgcolor': u"CCCCCC",
                    'created_at': datetime.now(), 'updated_at': datetime.now()
                }).returning(label.c.id, label.c.name)).first()

            proposals = conn.execute(
                    proposal.select().where(proposal.c.project_id == proj['id']).where(proposal.c.technical_level == tl_title)
                )
            for prop in proposals:
                pl = conn.execute(proposal_label.insert().values({
                    'proposal_id': prop['id'], 'label_id': lab['id'], 'created_at': datetime.now()
                }))

        # session type
        labset = conn.execute(labelset.insert().values({
                'project_id': proj['id'], 'name': u"session-type", 'title': u"Session Type",
                'seq': 1, 'description': "", 'radio_mode': True, 'restricted': True,
                'required': True, 'created_at': datetime.now(), 'updated_at': datetime.now()
            }).returning(labelset.c.id)).first()
        st_list = [('lecture', "Lecture"), ('demo', "Demo"), ('tutorial', "Tutorial"), ('workshop', "Workshop"), ('discussion', "Discussion"), ('panel', "Panel")]
        for index, st in enumerate(st_list):
            st_name, st_title = st
            lab = conn.execute(label.insert().values({
                    'name': st_name, 'title': st_title,
                    'labelset_id': labset[0], 'seq': index, 'bgcolor': u"CCCCCC",
                    'created_at': datetime.now(), 'updated_at': datetime.now()
                }).returning(label.c.id, label.c.name)).first()

            proposals = conn.execute(
                    proposal.select().where(proposal.c.project_id == proj['id']).where(proposal.c.session_type == st_title)
                )
            for prop in proposals:
                conn.execute(proposal_label.insert().values({
                        'proposal_id': prop['id'], 'label_id': lab['id'], 'created_at': datetime.now()
                    }))


def downgrade():
    conn = op.get_bind()
    conn.execute(labelset.delete())
    conn.execute(label.delete())
    conn.execute(proposal_label.delete())
