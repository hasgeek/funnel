# type: ignore
"""Remove and rename obsolete columns.

Revision ID: 1b8fc63c0fb0
Revises: ea20c403b240
Create Date: 2019-06-06 12:43:24.087572

"""

# revision identifiers, used by Alembic.
revision = '1b8fc63c0fb0'
down_revision = 'ea20c403b240'

import json

from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa

default_part_labels = {
    "proposal": {
        "part_a": {
            "title": "Abstract",
            "hint": "Give us a brief description of your talk, key takeaways for the audience and the"
            " intended audience.",
        },
        "part_b": {
            "title": "Outline",
            "hint": "Give us a break-up of your talk either in the form of draft slides, mind-map or"
            " text description.",
        },
    }
}


def upgrade() -> None:
    op.alter_column('proposal', 'objective_text', new_column_name='abstract_text')
    op.alter_column('proposal', 'objective_html', new_column_name='abstract_html')
    op.alter_column('proposal', 'description_text', new_column_name='outline_text')
    op.alter_column('proposal', 'description_html', new_column_name='outline_html')
    op.drop_column('project', 'labels')
    op.drop_column('proposal', 'technical_level')
    op.drop_column('proposal', 'session_type')


def downgrade() -> None:
    op.add_column(
        'proposal',
        sa.Column(
            'session_type', sa.VARCHAR(length=40), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        'proposal',
        sa.Column(
            'technical_level', sa.VARCHAR(length=40), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        'project',
        sa.Column(
            'labels',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'" + json.dumps(default_part_labels) + "'::jsonb"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.alter_column('project', 'labels', server_default=sa.text("'{}'::jsonb"))
    op.alter_column('proposal', 'abstract_text', new_column_name='objective_text')
    op.alter_column('proposal', 'abstract_html', new_column_name='objective_html')
    op.alter_column('proposal', 'outline_text', new_column_name='description_text')
    op.alter_column('proposal', 'outline_html', new_column_name='description_html')
