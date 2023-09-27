"""Record UserSession geonameid and ASN.

Revision ID: fb8eb6e5b70a
Revises: 64f0cfe37976
Create Date: 2021-04-28 03:24:28.554095

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'fb8eb6e5b70a'
down_revision = '64f0cfe37976'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        'user_session', sa.Column('geonameid_city', sa.Integer(), nullable=True)
    )
    op.add_column(
        'user_session', sa.Column('geonameid_subdivision', sa.Integer(), nullable=True)
    )
    op.add_column(
        'user_session', sa.Column('geonameid_country', sa.Integer(), nullable=True)
    )
    op.add_column('user_session', sa.Column('geoip_asn', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('user_session', 'geoip_asn')
    op.drop_column('user_session', 'geonameid_country')
    op.drop_column('user_session', 'geonameid_subdivision')
    op.drop_column('user_session', 'geonameid_city')
