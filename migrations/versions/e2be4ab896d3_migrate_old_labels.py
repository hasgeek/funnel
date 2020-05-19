"""migrate old labels

Revision ID: e2be4ab896d3
Revises: 0b25df40d307
Create Date: 2019-04-22 12:50:31.062089

"""

# revision identifiers, used by Alembic.
revision = 'e2be4ab896d3'
down_revision = '0b25df40d307'

from alembic import op
from sqlalchemy.sql import column, table
import sqlalchemy as sa

proposal = table(
    'proposal',
    column('id', sa.Integer()),
    column('project_id', sa.Integer()),
    column('technical_level', sa.Unicode(40)),
    column('session_type', sa.Unicode(40)),
    column('section_id', sa.Integer()),
)

project = table('project', column('id', sa.Integer()), column('name', sa.Unicode(250)))

section = table(
    'section',
    column('id', sa.Integer()),
    column('project_id', sa.Integer()),
    column('name', sa.Unicode(250)),
    column('title', sa.Unicode(250)),
    column('description', sa.UnicodeText()),
    column('created_at', sa.DateTime()),
    column('updated_at', sa.DateTime()),
)

label = table(
    'label',
    column('id', sa.Integer()),
    column('name', sa.Unicode(250)),
    column('title', sa.Unicode(250)),
    column('description', sa.UnicodeText()),
    column('icon_emoji', sa.UnicodeText()),
    column('project_id', sa.Integer()),
    column('main_label_id', sa.Integer()),
    column('seq', sa.Integer()),
    column('restricted', sa.Boolean()),
    column('required', sa.Boolean()),
    column('archived', sa.Boolean()),
    column('created_at', sa.DateTime()),
    column('updated_at', sa.DateTime()),
)

proposal_label = table(
    'proposal_label',
    column('proposal_id', sa.Integer()),
    column('label_id', sa.Integer()),
    column('created_at', sa.DateTime()),
)


def upgrade():
    conn = op.get_bind()
    # Migrate sections -
    projects = conn.execute(project.select())
    for proj in projects:
        sec_count = conn.scalar(
            sa.select([sa.func.count('*')])
            .select_from(section)
            .where(section.c.project_id == proj['id'])
        )
        if sec_count > 0:
            # the project has some sections
            # create section labelset for the project
            sections_label = conn.execute(
                label.insert()
                .values(
                    {
                        'project_id': proj['id'],
                        'name': "section",
                        'title': "Section",
                        'seq': 1,
                        'description': "",
                        'restricted': False,
                        'archived': False,
                        'required': True,
                        'created_at': sa.func.now(),
                        'updated_at': sa.func.now(),
                    }
                )
                .returning(label.c.id)
            ).first()

            sections = conn.execute(
                section.select().where(section.c.project_id == proj['id'])
            )
            for index, sec in enumerate(sections, start=1):
                lab = conn.execute(
                    label.insert()
                    .values(
                        {
                            'main_label_id': sections_label[0],
                            'project_id': proj['id'],
                            'name': sec['name'],
                            'title': sec['title'],
                            'seq': index,
                            'description': "",
                            'restricted': False,
                            'archived': False,
                            'required': True,
                            'created_at': sa.func.now(),
                            'updated_at': sa.func.now(),
                        }
                    )
                    .returning(label.c.id, label.c.name)
                ).first()

                # FIXME: This will miss proposals in a project linked to sections in another project
                # -- an error condition resulting from proposals that have been moved around
                proposals = conn.execute(
                    proposal.select()
                    .where(proposal.c.section_id == sec['id'])
                    .where(proposal.c.project_id == sec['project_id'])
                )
                for prop in proposals:
                    conn.execute(
                        proposal_label.insert().values(
                            {
                                'proposal_id': prop['id'],
                                'label_id': lab['id'],
                                'created_at': sa.func.now(),
                            }
                        )
                    )

        # technical level
        techlevel_label = conn.execute(
            label.insert()
            .values(
                {
                    'project_id': proj['id'],
                    'name': "technical-level",
                    'title': "Technical level",
                    'seq': 2,
                    'description': "",
                    'restricted': False,
                    'archived': False,
                    'required': True,
                    'created_at': sa.func.now(),
                    'updated_at': sa.func.now(),
                }
            )
            .returning(label.c.id)
        ).first()
        tl_list = [
            ('beginner', "Beginner"),
            ('intermediate', "Intermediate"),
            ('advanced', "Advanced"),
        ]
        for index, tl in enumerate(tl_list, start=1):
            tl_name, tl_title = tl
            lab = conn.execute(
                label.insert()
                .values(
                    {
                        'project_id': proj['id'],
                        'name': tl_name,
                        'title': tl_title,
                        'main_label_id': techlevel_label[0],
                        'seq': index,
                        'description': "",
                        'restricted': False,
                        'archived': False,
                        'required': True,
                        'created_at': sa.func.now(),
                        'updated_at': sa.func.now(),
                    }
                )
                .returning(label.c.id, label.c.name)
            ).first()

            proposals = conn.execute(
                proposal.select()
                .where(proposal.c.project_id == proj['id'])
                .where(proposal.c.technical_level == tl_title)
            )
            for prop in proposals:
                conn.execute(
                    proposal_label.insert().values(
                        {
                            'proposal_id': prop['id'],
                            'label_id': lab['id'],
                            'created_at': sa.func.now(),
                        }
                    )
                )

        # session type
        sessiontype_label = conn.execute(
            label.insert()
            .values(
                {
                    'project_id': proj['id'],
                    'name': "session-type",
                    'title': "Session type",
                    'seq': 3,
                    'description': "",
                    'restricted': False,
                    'archived': False,
                    'required': False,
                    'created_at': sa.func.now(),
                    'updated_at': sa.func.now(),
                }
            )
            .returning(label.c.id)
        ).first()

        st_list = [
            ('lecture', "Lecture"),
            ('demo', "Demo"),
            ('tutorial', "Tutorial"),
            ('workshop', "Workshop"),
            ('discussion', "Discussion"),
            ('panel', "Panel"),
        ]

        for index, st in enumerate(st_list, start=1):
            st_name, st_title = st
            duplicate_count = conn.scalar(
                sa.select([sa.func.count('*')])
                .select_from(label)
                .where(label.c.name == st_name)
                .where(label.c.project_id == proj['id'])
            )
            if duplicate_count > 0:
                st_name = st_name + "2"
            lab = conn.execute(
                label.insert()
                .values(
                    {
                        'project_id': proj['id'],
                        'name': st_name,
                        'title': st_title,
                        'main_label_id': sessiontype_label[0],
                        'seq': index,
                        'description': "",
                        'restricted': False,
                        'archived': False,
                        'required': True,
                        'created_at': sa.func.now(),
                        'updated_at': sa.func.now(),
                    }
                )
                .returning(label.c.id, label.c.name)
            ).first()

            proposals = conn.execute(
                proposal.select()
                .where(proposal.c.project_id == proj['id'])
                .where(proposal.c.session_type == st_title)
            )
            for prop in proposals:
                conn.execute(
                    proposal_label.insert().values(
                        {
                            'proposal_id': prop['id'],
                            'label_id': lab['id'],
                            'created_at': sa.func.now(),
                        }
                    )
                )


def downgrade():
    conn = op.get_bind()
    conn.execute(label.delete())
    conn.execute(proposal_label.delete())
