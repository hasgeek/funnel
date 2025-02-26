"""GeoIP databases."""

import os.path
from dataclasses import dataclass

from flask import Flask
from geoip2.database import Reader
from geoip2.errors import AddressNotFoundError, GeoIP2Error
from geoip2.models import ASN, City

__all__ = ['AddressNotFoundError', 'GeoIP', 'GeoIP2Error', 'geoip']


@dataclass
class GeoIP:
    """Wrapper for GeoIP2 Reader."""

    city_db: Reader | None = None
    asn_db: Reader | None = None

    def __bool__(self) -> bool:
        return self.city_db is not None or self.asn_db is not None

    def city(self, ipaddr: str) -> City | None:
        if self.city_db:
            return self.city_db.city(ipaddr)
        return None

    def asn(self, ipaddr: str) -> ASN | None:
        if self.asn_db:
            return self.asn_db.asn(ipaddr)
        return None

    def init_app(self, app: Flask) -> None:
        if 'GEOIP_DB_CITY' in app.config:
            if not os.path.exists(app.config['GEOIP_DB_CITY']):
                app.logger.warning(
                    "GeoIP city database missing at %s", app.config['GEOIP_DB_CITY']
                )
            else:
                self.city_db = Reader(app.config['GEOIP_DB_CITY'])

        if 'GEOIP_DB_ASN' in app.config:
            if not os.path.exists(app.config['GEOIP_DB_ASN']):
                app.logger.warning(
                    "GeoIP ASN database missing at %s", app.config['GEOIP_DB_ASN']
                )
            else:
                self.asn_db = Reader(app.config['GEOIP_DB_ASN'])


# Export a singleton
geoip = GeoIP()
