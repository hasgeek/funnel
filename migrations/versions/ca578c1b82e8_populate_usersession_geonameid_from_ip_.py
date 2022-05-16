"""Populate UserSession geonameid from IP address.

Revision ID: ca578c1b82e8
Revises: fb8eb6e5b70a
Create Date: 2021-04-28 18:02:29.867574

"""

from types import SimpleNamespace

from alembic import op
from sqlalchemy.sql import column, table
import sqlalchemy as sa

from progressbar import ProgressBar
import progressbar.widgets

try:
    import geoip2.database as geoip2_database
    import geoip2.errors as geoip2_errors
except ImportError:
    geoip2_database = None  # type: ignore[assignment]
    geoip2_errors = SimpleNamespace(GeoIP2Error=Exception)  # type: ignore[assignment]


# revision identifiers, used by Alembic.
revision = 'ca578c1b82e8'
down_revision = 'fb8eb6e5b70a'
branch_labels = None
depends_on = None

GEOIP_DB_CITY = '/usr/share/GeoIP/GeoLite2-City.mmdb'
GEOIP_DB_ASN = '/usr/share/GeoIP/GeoLite2-ASN.mmdb'

user_session = table(
    'user_session',
    column('id', sa.Integer()),
    column('ipaddr', sa.String()),
    column('geonameid_city', sa.Integer()),
    column('geonameid_subdivision', sa.Integer()),
    column('geonameid_country', sa.Integer()),
    column('geoip_asn', sa.Integer()),
)


def get_progressbar(label, maxval):
    return ProgressBar(
        maxval=maxval,
        widgets=[
            label,
            ': ',
            progressbar.widgets.Percentage(),
            ' ',
            progressbar.widgets.Bar(),
            ' ',
            progressbar.widgets.ETA(),
            ' ',
        ],
    )


def upgrade():
    if geoip2_database is not None:
        try:
            geoip_city = geoip2_database.Reader(GEOIP_DB_CITY)
        except FileNotFoundError:
            geoip_city = None
        try:
            geoip_asn = geoip2_database.Reader(GEOIP_DB_ASN)
        except FileNotFoundError:
            geoip_asn = None

        if geoip_city is not None or geoip_asn is not None:
            conn = op.get_bind()
            count = conn.scalar(
                sa.select([sa.func.count('*')])
                .select_from(user_session)
                .where(
                    sa.or_(
                        user_session.c.geonameid_city.is_(None),
                        user_session.c.geoip_asn.is_(None),
                    )
                )
            )
            progress = get_progressbar("User sessions", count)
            progress.start()
            sessions = conn.execute(
                sa.select([user_session.c.id, user_session.c.ipaddr]).where(
                    sa.or_(
                        user_session.c.geonameid_city.is_(None),
                        user_session.c.geoip_asn.is_(None),
                    )
                )
            )
            for counter, row in enumerate(sessions):
                if row.ipaddr:
                    lookup_city = None
                    lookup_subdivision = None
                    lookup_country = None
                    lookup_asn = None
                    if geoip_city:
                        try:
                            city_lookup = geoip_city.city(row.ipaddr)
                            lookup_city = city_lookup.city.geoname_id
                            lookup_subdivision = (
                                city_lookup.subdivisions.most_specific.geoname_id
                            )
                            lookup_country = city_lookup.country.geoname_id
                        except geoip2_errors.GeoIP2Error:
                            pass
                    if geoip_asn:
                        try:
                            lookup_asn = geoip_asn.asn(
                                row.ipaddr
                            ).autonomous_system_number
                        except geoip2_errors.GeoIP2Error:
                            pass
                    conn.execute(
                        user_session.update()
                        .where(user_session.c.id == row.id)
                        .values(
                            geonameid_city=lookup_city,
                            geonameid_subdivision=lookup_subdivision,
                            geonameid_country=lookup_country,
                            geoip_asn=lookup_asn,
                        )
                    )
                progress.update(counter)
            progress.finish()
        else:
            print("Skipping geonameid population as databases are missing")
    else:
        print(  # type: ignore[unreachable]
            "Skipping geonameid population as geoip2 is not installed"
        )


def downgrade():
    pass
