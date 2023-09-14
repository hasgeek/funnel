"""Add geoname models.

Revision ID: 7d5b77aada1e
Revises: 896137ace892
Create Date: 2021-06-19 17:05:32.356693

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7d5b77aada1e'
down_revision = '896137ace892'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade(engine_name=''):
    # Do not modify. Edit `upgrade_` instead
    globals().get('upgrade_%s' % engine_name, lambda: None)()


def downgrade(engine_name=''):
    # Do not modify. Edit `downgrade_` instead
    globals().get('downgrade_%s' % engine_name, lambda: None)()


def upgrade_():
    pass


def downgrade_():
    pass


def upgrade_geoname():
    op.create_table(
        'geo_country_info',
        sa.Column('iso_alpha2', sa.CHAR(length=2), nullable=True),
        sa.Column('iso_alpha3', sa.CHAR(length=3), nullable=True),
        sa.Column('iso_numeric', sa.Integer(), nullable=True),
        sa.Column('fips_code', sa.Unicode(length=3), nullable=True),
        sa.Column('capital', sa.Unicode(), nullable=True),
        sa.Column('area_in_sqkm', sa.Numeric(), nullable=True),
        sa.Column('population', sa.BigInteger(), nullable=True),
        sa.Column('continent', sa.CHAR(length=2), nullable=True),
        sa.Column('tld', sa.Unicode(length=3), nullable=True),
        sa.Column('currency_code', sa.CHAR(length=3), nullable=True),
        sa.Column('currency_name', sa.Unicode(), nullable=True),
        sa.Column('phone', sa.Unicode(length=16), nullable=True),
        sa.Column('postal_code_format', sa.Unicode(), nullable=True),
        sa.Column('postal_code_regex', sa.Unicode(), nullable=True),
        sa.Column(
            'languages', postgresql.ARRAY(sa.Unicode(), dimensions=1), nullable=True
        ),
        sa.Column(
            'neighbours',
            postgresql.ARRAY(sa.CHAR(length=2), dimensions=1),
            nullable=True,
        ),
        sa.Column('equivalent_fips_code', sa.Unicode(length=3), nullable=True),
        sa.Column('name', sa.Unicode(length=250), nullable=False),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('iso_alpha2'),
        sa.UniqueConstraint('iso_alpha3'),
        sa.UniqueConstraint('name'),
    )
    op.create_table(
        'geo_admin1_code',
        sa.Column('title', sa.Unicode(), nullable=True),
        sa.Column('ascii_title', sa.Unicode(), nullable=True),
        sa.Column('country', sa.CHAR(length=2), nullable=True),
        sa.Column('admin1_code', sa.Unicode(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['country'],
            ['geo_country_info.iso_alpha2'],
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'geo_admin2_code',
        sa.Column('title', sa.Unicode(), nullable=True),
        sa.Column('ascii_title', sa.Unicode(), nullable=True),
        sa.Column('country', sa.CHAR(length=2), nullable=True),
        sa.Column('admin1_code', sa.Unicode(), nullable=True),
        sa.Column('admin2_code', sa.Unicode(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['country'],
            ['geo_country_info.iso_alpha2'],
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'geo_name',
        sa.Column('ascii_title', sa.Unicode(), nullable=True),
        sa.Column('latitude', sa.Numeric(), nullable=True),
        sa.Column('longitude', sa.Numeric(), nullable=True),
        sa.Column('fclass', sa.CHAR(length=1), nullable=True),
        sa.Column('fcode', sa.Unicode(), nullable=True),
        sa.Column('country', sa.CHAR(length=2), nullable=True),
        sa.Column('cc2', sa.Unicode(), nullable=True),
        sa.Column('admin1', sa.Unicode(), nullable=True),
        sa.Column('admin1_id', sa.Integer(), nullable=True),
        sa.Column('admin2', sa.Unicode(), nullable=True),
        sa.Column('admin2_id', sa.Integer(), nullable=True),
        sa.Column('admin4', sa.Unicode(), nullable=True),
        sa.Column('admin3', sa.Unicode(), nullable=True),
        sa.Column('population', sa.BigInteger(), nullable=True),
        sa.Column('elevation', sa.Integer(), nullable=True),
        sa.Column('dem', sa.Integer(), nullable=True),
        sa.Column('timezone', sa.Unicode(), nullable=True),
        sa.Column('moddate', sa.Date(), nullable=True),
        sa.Column('name', sa.Unicode(length=250), nullable=False),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['admin1_id'],
            ['geo_admin1_code.id'],
        ),
        sa.ForeignKeyConstraint(
            ['admin2_id'],
            ['geo_admin2_code.id'],
        ),
        sa.ForeignKeyConstraint(
            ['country'],
            ['geo_country_info.iso_alpha2'],
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_table(
        'geo_alt_name',
        sa.Column('geonameid', sa.Integer(), nullable=False),
        sa.Column('lang', sa.Unicode(), nullable=True),
        sa.Column('title', sa.Unicode(), nullable=False),
        sa.Column('is_preferred_name', sa.Boolean(), nullable=False),
        sa.Column('is_short_name', sa.Boolean(), nullable=False),
        sa.Column('is_colloquial', sa.Boolean(), nullable=False),
        sa.Column('is_historic', sa.Boolean(), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['geonameid'],
            ['geo_name.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_geo_alt_name_lang'), 'geo_alt_name', ['lang'], unique=False
    )

    op.execute(
        sa.DDL(
            'CREATE INDEX ix_geo_country_info_title ON geo_country_info'
            ' (lower(title) varchar_pattern_ops);'
        )
    )
    op.execute(
        sa.DDL(
            'CREATE INDEX ix_geo_name_title ON geo_name'
            ' (lower(title) varchar_pattern_ops);'
        )
    )
    op.execute(
        sa.DDL(
            'CREATE INDEX ix_geo_name_ascii_title ON geo_name'
            ' (lower(ascii_title) varchar_pattern_ops);'
        )
    )

    op.execute(
        sa.DDL(
            'CREATE INDEX ix_geo_alt_name_title ON geo_alt_name'
            ' (lower(title) varchar_pattern_ops);'
        )
    )


def downgrade_geoname():
    op.drop_index(op.f('ix_geo_alt_name_title'), table_name='geo_alt_name')
    op.drop_index(op.f('ix_geo_name_ascii_title'), table_name='geo_name')
    op.drop_index(op.f('ix_geo_name_title'), table_name='geo_name')
    op.drop_index(op.f('ix_geo_country_info_title'), table_name='geo_country_info')
    op.drop_index(op.f('ix_geo_alt_name_lang'), table_name='geo_alt_name')
    op.drop_table('geo_alt_name')
    op.drop_table('geo_name')
    op.drop_table('geo_admin2_code')
    op.drop_table('geo_admin1_code')
    op.drop_table('geo_country_info')
