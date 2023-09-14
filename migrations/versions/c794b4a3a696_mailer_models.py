"""Mailer models.

Revision ID: c794b4a3a696
Revises: f346a7cc783a
Create Date: 2023-07-12 12:47:04.719705

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c794b4a3a696'
down_revision: str = 'f346a7cc783a'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade(engine_name: str = '') -> None:
    """Upgrade all databases."""
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name: str = '') -> None:
    """Downgrade all databases."""
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    """Upgrade database bind ''."""
    op.create_table(
        'mailer',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('name', sa.Unicode(length=250), nullable=False),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.Column('user_uuid', sa.Uuid(), nullable=False),
        sa.Column('status', sa.Integer(), nullable=False),
        sa.Column('fields', sa.UnicodeText(), nullable=False),
        sa.Column('trackopens', sa.Boolean(), nullable=False),
        sa.Column('stylesheet', sa.UnicodeText(), nullable=False),
        sa.Column('cc', sa.UnicodeText(), nullable=True),
        sa.Column('bcc', sa.UnicodeText(), nullable=True),
        sa.ForeignKeyConstraint(
            ['user_uuid'],
            ['user.uuid'],
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_table(
        'mailer_draft',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('url_id', sa.Integer(), nullable=False),
        sa.Column('mailer_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.Unicode(length=250), nullable=False),
        sa.Column('template', sa.UnicodeText(), nullable=False),
        sa.ForeignKeyConstraint(
            ['mailer_id'],
            ['mailer.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mailer_id', 'url_id'),
    )
    op.create_table(
        'mailer_recipient',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('url_id', sa.Integer(), nullable=False),
        sa.Column('mailer_id', sa.Integer(), nullable=False),
        sa.Column('fullname', sa.Unicode(length=80), nullable=True),
        sa.Column('firstname', sa.Unicode(length=80), nullable=True),
        sa.Column('lastname', sa.Unicode(length=80), nullable=True),
        sa.Column('nickname', sa.Unicode(length=80), nullable=True),
        sa.Column('email', sa.Unicode(length=80), nullable=False),
        sa.Column('md5sum', sa.String(length=32), nullable=False),
        sa.Column(
            'data',
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), 'postgresql'
            ),
            nullable=False,
        ),
        sa.Column('is_sent', sa.Boolean(), nullable=False),
        sa.Column('opentoken', sa.Unicode(length=44), nullable=False),
        sa.Column('opened', sa.Boolean(), nullable=False),
        sa.Column('opened_ipaddr', sa.Unicode(length=45), nullable=True),
        sa.Column('opened_first_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('opened_last_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('opened_count', sa.Integer(), nullable=False),
        sa.Column('rsvptoken', sa.Unicode(length=44), nullable=False),
        sa.Column('rsvp', sa.Unicode(length=1), nullable=True),
        sa.Column('subject', sa.Unicode(length=250), nullable=True),
        sa.Column('template', sa.UnicodeText(), nullable=True),
        sa.Column('rendered_text', sa.UnicodeText(), nullable=True),
        sa.Column('rendered_html', sa.UnicodeText(), nullable=True),
        sa.Column('draft_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ['draft_id'],
            ['mailer_draft.id'],
        ),
        sa.ForeignKeyConstraint(
            ['mailer_id'],
            ['mailer.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mailer_id', 'url_id'),
        sa.UniqueConstraint('opentoken'),
        sa.UniqueConstraint('rsvptoken'),
    )
    with op.batch_alter_table('mailer_recipient', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_mailer_recipient_email'), ['email'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_mailer_recipient_md5sum'), ['md5sum'], unique=False
        )


def downgrade_() -> None:
    """Downgrade database bind ''."""
    with op.batch_alter_table('mailer_recipient', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_mailer_recipient_md5sum'))
        batch_op.drop_index(batch_op.f('ix_mailer_recipient_email'))

    op.drop_table('mailer_recipient')
    op.drop_table('mailer_draft')
    op.drop_table('mailer')
