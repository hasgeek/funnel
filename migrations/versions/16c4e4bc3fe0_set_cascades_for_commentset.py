"""Set cascades for commentset.

Revision ID: 16c4e4bc3fe0
Revises: d79beb04a529
Create Date: 2024-02-03 15:42:49.051319

"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '16c4e4bc3fe0'
down_revision: str = 'd79beb04a529'
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
    """Upgrade default database."""
    with op.batch_alter_table('comment', schema=None) as batch_op:
        batch_op.drop_constraint('comment_commentset_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(
            'comment_commentset_id_fkey',
            'commentset',
            ['commentset_id'],
            ['id'],
            ondelete='CASCADE',
        )
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.drop_constraint('project_commentset_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(
            'project_commentset_id_fkey',
            'commentset',
            ['commentset_id'],
            ['id'],
            ondelete='RESTRICT',
        )
    with op.batch_alter_table('proposal', schema=None) as batch_op:
        batch_op.drop_constraint('proposal_commentset_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(
            'proposal_commentset_id_fkey',
            'commentset',
            ['commentset_id'],
            ['id'],
            ondelete='RESTRICT',
        )
    with op.batch_alter_table('update', schema=None) as batch_op:
        batch_op.drop_constraint('update_commentset_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(
            'update_commentset_id_fkey',
            'commentset',
            ['commentset_id'],
            ['id'],
            ondelete='RESTRICT',
        )


def downgrade_() -> None:
    """Downgrade default database."""
    with op.batch_alter_table('update', schema=None) as batch_op:
        batch_op.drop_constraint('update_commentset_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(
            'update_commentset_id_fkey', 'commentset', ['commentset_id'], ['id']
        )
    with op.batch_alter_table('proposal', schema=None) as batch_op:
        batch_op.drop_constraint('proposal_commentset_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(
            'proposal_commentset_id_fkey', 'commentset', ['commentset_id'], ['id']
        )
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.drop_constraint('project_commentset_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(
            'project_commentset_id_fkey', 'commentset', ['commentset_id'], ['id']
        )
    with op.batch_alter_table('comment', schema=None) as batch_op:
        batch_op.drop_constraint('comment_commentset_id_fkey', type_='foreignkey')
        batch_op.create_foreign_key(
            'comment_commentset_id_fkey', 'commentset', ['commentset_id'], ['id']
        )
