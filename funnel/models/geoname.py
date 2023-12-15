"""Geoname data models."""

from __future__ import annotations

import re
from collections.abc import Collection
from datetime import date
from decimal import Decimal
from typing import Self, cast

from sqlalchemy.dialects.postgresql import ARRAY

from coaster.utils import make_name

from . import (
    BaseMixin,
    BaseNameMixin,
    GeonameModel,
    Mapped,
    Query,
    db,
    relationship,
    sa,
    sa_orm,
    types,
)
from .helpers import quote_autocomplete_like

__all__ = ['GeoName', 'GeoCountryInfo', 'GeoAdmin1Code', 'GeoAdmin2Code', 'GeoAltName']


NOWORDS_RE = re.compile(r'(\W+)', re.UNICODE)
WORDS_RE = re.compile(r'\w+', re.UNICODE)

continent_codes = {
    'AF': 6255146,  # Africa
    'AS': 6255147,  # Asia
    'EU': 6255148,  # Europe
    'NA': 6255149,  # North America
    'OC': 6255151,  # Oceania
    'SA': 6255150,  # South America
    'AN': 6255152,  # Antarctica
}


class GeoCountryInfo(BaseNameMixin, GeonameModel):
    """Geoname record for a country."""

    __tablename__ = 'geo_country_info'

    geonameid: Mapped[int] = sa_orm.synonym('id')
    geoname: Mapped[GeoName | None] = relationship(
        uselist=False,
        viewonly=True,
        primaryjoin=lambda: GeoCountryInfo.id == sa_orm.foreign(GeoName.id),
        back_populates='has_country',
    )
    iso_alpha2: Mapped[types.char2 | None] = sa_orm.mapped_column(
        sa.CHAR(2), unique=True
    )
    iso_alpha3: Mapped[types.char3 | None] = sa_orm.mapped_column(unique=True)
    iso_numeric: Mapped[int | None]
    fips_code: Mapped[types.str3 | None]
    capital: Mapped[str | None]
    area_in_sqkm: Mapped[Decimal | None]
    population: Mapped[types.bigint | None]
    continent: Mapped[types.char2 | None]
    tld: Mapped[types.str3 | None]
    currency_code: Mapped[types.char3 | None]
    currency_name: Mapped[str | None]
    phone: Mapped[types.str16 | None]
    postal_code_format: Mapped[types.unicode | None]
    postal_code_regex: Mapped[types.unicode | None]
    languages: Mapped[list[str] | None] = sa_orm.mapped_column(
        ARRAY(sa.Unicode, dimensions=1)
    )
    neighbours: Mapped[list[str] | None] = sa_orm.mapped_column(
        ARRAY(sa.CHAR(2), dimensions=1)
    )
    equivalent_fips_code: Mapped[types.str3]

    __table_args__ = (
        sa.Index(
            'ix_geo_country_info_title',
            sa.func.lower('title').label('title_lower'),
            postgresql_ops={'title_lower': 'varchar_pattern_ops'},
        ),
    )

    def __repr__(self) -> str:
        """Return representation."""
        return f'<GeoCountryInfo {self.geonameid} "{self.title}">'


class GeoAdmin1Code(BaseMixin, GeonameModel):
    """Geoname record for 1st level administrative division (state, province)."""

    __tablename__ = 'geo_admin1_code'

    geonameid: Mapped[int] = sa_orm.synonym('id')
    geoname: Mapped[GeoName | None] = relationship(
        uselist=False,
        primaryjoin=lambda: GeoAdmin1Code.id == sa_orm.foreign(GeoName.id),
        viewonly=True,
        back_populates='has_admin1code',
    )
    title: Mapped[str | None] = sa_orm.mapped_column(sa.Unicode)
    ascii_title: Mapped[str | None] = sa_orm.mapped_column(sa.Unicode)
    country_id: Mapped[str | None] = sa_orm.mapped_column(
        'country', sa.CHAR(2), sa.ForeignKey('geo_country_info.iso_alpha2')
    )
    country: Mapped[GeoCountryInfo | None] = relationship('GeoCountryInfo')
    admin1_code: Mapped[str | None] = sa_orm.mapped_column(sa.Unicode)

    def __repr__(self) -> str:
        """Return representation."""
        return f'<GeoAdmin1Code {self.geonameid} "self.ascii_title">'


class GeoAdmin2Code(BaseMixin, GeonameModel):
    """Geoname record for 2nd level administrative division (district, county)."""

    __tablename__ = 'geo_admin2_code'

    geonameid: Mapped[int] = sa_orm.synonym('id')
    geoname: Mapped[GeoName] = relationship(
        'GeoName',
        uselist=False,
        viewonly=True,
        primaryjoin=lambda: GeoAdmin2Code.id == sa_orm.foreign(GeoName.id),
        back_populates='has_admin2code',
    )
    title: Mapped[str | None] = sa_orm.mapped_column(sa.Unicode)
    ascii_title: Mapped[str | None] = sa_orm.mapped_column(sa.Unicode)
    country_id: Mapped[str | None] = sa_orm.mapped_column(
        'country', sa.CHAR(2), sa.ForeignKey('geo_country_info.iso_alpha2')
    )
    country: Mapped[GeoCountryInfo | None] = relationship('GeoCountryInfo')
    admin1_code: Mapped[str | None] = sa_orm.mapped_column(sa.Unicode)
    admin2_code: Mapped[str | None] = sa_orm.mapped_column(sa.Unicode)

    def __repr__(self) -> str:
        """Return representation."""
        return f'<GeoAdmin2Code {self.geonameid} "self.ascii_title">'


class GeoName(BaseNameMixin, GeonameModel):
    """Geographical name record."""

    __tablename__ = 'geo_name'

    geonameid: Mapped[int] = sa_orm.synonym('id')
    ascii_title: Mapped[str | None] = sa_orm.mapped_column(sa.Unicode)
    latitude: Mapped[Decimal | None] = sa_orm.mapped_column(sa.Numeric)
    longitude: Mapped[Decimal | None] = sa_orm.mapped_column(sa.Numeric)
    fclass: Mapped[str | None] = sa_orm.mapped_column(sa.CHAR(1))
    fcode: Mapped[str | None] = sa_orm.mapped_column(sa.Unicode)
    country_id: Mapped[str | None] = sa_orm.mapped_column(
        'country', sa.CHAR(2), sa.ForeignKey('geo_country_info.iso_alpha2')
    )
    country: Mapped[GeoCountryInfo | None] = relationship('GeoCountryInfo')
    cc2: Mapped[str | None] = sa_orm.mapped_column(sa.Unicode)
    admin1: Mapped[str | None] = sa_orm.mapped_column(sa.Unicode)
    admin1_ref: Mapped[GeoAdmin1Code | None] = relationship(
        'GeoAdmin1Code',
        uselist=False,
        primaryjoin=lambda: sa.and_(
            GeoName.country_id == sa_orm.foreign(GeoAdmin1Code.country_id),
            GeoName.admin1 == sa_orm.foreign(GeoAdmin1Code.admin1_code),
        ),
        viewonly=True,
    )
    admin1_id: Mapped[int | None] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('geo_admin1_code.id'), nullable=True
    )
    admin1code: Mapped[GeoAdmin1Code | None] = relationship(
        'GeoAdmin1Code', uselist=False, foreign_keys=[admin1_id]
    )

    admin2: Mapped[str | None] = sa_orm.mapped_column(sa.Unicode)
    admin2_ref: Mapped[GeoAdmin2Code | None] = relationship(
        'GeoAdmin2Code',
        uselist=False,
        primaryjoin=lambda: sa.and_(
            GeoName.country_id == sa_orm.foreign(GeoAdmin2Code.country_id),
            GeoName.admin1 == sa_orm.foreign(GeoAdmin2Code.admin1_code),
            GeoName.admin2 == sa_orm.foreign(GeoAdmin2Code.admin2_code),
        ),
        viewonly=True,
    )
    admin2_id: Mapped[int | None] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('geo_admin2_code.id'), nullable=True
    )
    admin2code: Mapped[GeoAdmin2Code | None] = relationship(
        'GeoAdmin2Code', uselist=False, foreign_keys=[admin2_id]
    )

    admin4: Mapped[str | None] = sa_orm.mapped_column(sa.Unicode)
    admin3: Mapped[str | None] = sa_orm.mapped_column(sa.Unicode)
    population: Mapped[int | None] = sa_orm.mapped_column(sa.BigInteger)
    elevation: Mapped[int | None] = sa_orm.mapped_column(sa.Integer)
    #: Digital Elevation Model
    dem: Mapped[int | None] = sa_orm.mapped_column(sa.Integer)
    timezone: Mapped[str | None] = sa_orm.mapped_column(sa.Unicode)
    moddate: Mapped[date | None] = sa_orm.mapped_column(sa.Date)

    has_country: Mapped[GeoCountryInfo | None] = relationship(
        uselist=False,
        viewonly=True,
        primaryjoin=lambda: GeoCountryInfo.id == sa_orm.foreign(GeoName.id),
        back_populates='geoname',
    )
    has_admin1code: Mapped[GeoAdmin1Code | None] = relationship(
        uselist=False,
        viewonly=True,
        primaryjoin=lambda: GeoAdmin1Code.id == sa_orm.foreign(GeoName.id),
        back_populates='geoname',
    )
    has_admin2code: Mapped[GeoAdmin2Code | None] = relationship(
        uselist=False,
        viewonly=True,
        primaryjoin=lambda: GeoAdmin2Code.id == sa_orm.foreign(GeoName.id),
        back_populates='geoname',
    )
    alternate_titles: Mapped[list[GeoAltName]] = relationship()

    __table_args__ = (
        sa.Index(
            'ix_geo_name_title',
            sa.func.lower('title').label('title_lower'),
            postgresql_ops={'title_lower': 'varchar_pattern_ops'},
        ),
        sa.Index(
            'ix_geo_name_ascii_title',
            sa.func.lower(ascii_title).label('ascii_title_lower'),
            postgresql_ops={'ascii_title_lower': 'varchar_pattern_ops'},
        ),
    )

    @property
    def short_title(self) -> str:
        """Return a short title for this geoname record."""
        if self.has_country:
            return self.has_country.title
        if self.has_admin1code:
            return (
                self.admin1code.title
                if self.admin1code
                else self.admin1_ref.title
                if self.admin1_ref
                else ''
            ) or ''
        if self.has_admin2code:
            return (
                self.admin2code.title
                if self.admin2code
                else self.admin2_ref.title
                if self.admin2_ref
                else ''
            ) or ''
        return self.ascii_title or self.title

    @property
    def picker_title(self) -> str:
        """Return a disambiguation title for this geoname record."""
        title = self.use_title
        country = self.country_id
        if country == 'US':
            state = self.admin1
        else:
            state = None
        suffix = None

        if (self.fclass, self.fcode) == ('L', 'CONT'):
            suffix = 'continent'
            country = None
            state = None
        elif self.has_country:
            suffix = 'country'
            country = None
            state = None
        elif self.has_admin1code:
            if country in ('CA', 'CN', 'AF'):
                suffix = 'province'
            else:
                suffix = 'state'
            state = None
        elif self.has_admin2code:
            if country == 'US':
                suffix = 'county'
            elif country == 'CN':
                suffix = 'prefecture'
            else:
                suffix = 'district'

        if state:
            title = f'{title}, {state}'
        if country:
            title = f'{title}, {country}'
        if suffix:
            return f'{title} ({suffix})'
        return title

    @property
    def geoname(self) -> GeoName:
        """Return geoname record (self!)."""
        return self

    @property
    def use_title(self) -> str:
        """Return a recommended usable title (English-only)."""
        usetitle = self.ascii_title or ''
        if self.fclass == 'A' and self.fcode and self.fcode.startswith('PCL'):
            if 'of the' in usetitle:
                usetitle = usetitle.split('of the')[-1].strip()
            elif 'of The' in usetitle:
                usetitle = usetitle.split('of The')[-1].strip()
            elif 'of' in usetitle:
                usetitle = usetitle.split('of')[-1].strip()
        elif self.fclass == 'A' and self.fcode == 'ADM1':
            usetitle = (
                usetitle.replace('State of', '')
                .replace('Union Territory of', '')
                .strip()
            )
        return usetitle

    def make_name(self, reserved: Collection[str] = ()) -> None:
        """Create a unique name for this geoname record."""
        if self.ascii_title:
            usetitle = self.use_title
            if self.id:  # pylint: disable=using-constant-test

                def checkused(c: str) -> bool:
                    return bool(
                        c in reserved
                        or GeoName.query.filter(GeoName.id != self.id)
                        .filter_by(name=c)
                        .notempty()
                    )

            else:

                def checkused(c: str) -> bool:
                    return bool(
                        c in reserved or GeoName.query.filter_by(name=c).notempty()
                    )

            with db.session.no_autoflush:
                # pylint: disable=attribute-defined-outside-init
                self.name = str(make_name(usetitle, maxlength=250, checkused=checkused))

    def __repr__(self) -> str:
        """Return representation."""
        return (
            f'<GeoName {self.geonameid} {self.country_id} {self.fclass} {self.fcode}'
            f' "{self.ascii_title}">'
        )

    def related_geonames(self) -> dict[str, GeoName]:
        """Return related geonames based on superior hierarchy (country, state, etc)."""
        related: dict[str, GeoName] = {}
        if self.admin2code and self.admin2code.geonameid != self.geonameid:
            related['admin2'] = self.admin2code.geoname
        if self.admin1code and self.admin1code.geonameid != self.geonameid:
            related['admin1'] = self.admin1code.geoname
        if (
            self.country
            and self.country.geonameid != self.geonameid
            and self.country.geoname
        ):
            related['country'] = self.country.geoname
        if (
            (self.fclass, self.fcode) != ('L', 'CONT')
            and self.country
            and self.country.continent
        ):
            continent = GeoName.query.get(continent_codes[self.country.continent])
            if continent:
                related['continent'] = continent

        return related

    def as_dict(self, related=True, alternate_titles=True) -> dict:
        """Convert this record into a dictionary suitable for casting to JSON."""
        return {
            'geonameid': self.geonameid,
            'name': self.name,
            'title': self.title,
            'ascii_title': self.ascii_title,
            'short_title': self.short_title,
            'use_title': self.use_title,
            'picker_title': self.picker_title,
            'latitude': str(self.latitude),
            'longitude': str(self.longitude),
            'fclass': self.fclass,
            'fcode': self.fcode,
            'country': self.country_id,
            'cc2': self.cc2,
            'admin1': self.admin1,
            'admin2': self.admin2,
            'admin3': self.admin3,
            'admin4': self.admin4,
            'is_country': bool(self.has_country),
            'is_admin1': bool(self.has_admin1code),
            'is_admin2': bool(self.has_admin2code),
            'is_continent': (self.fclass, self.fcode) == ('L', 'CONT'),
            'population': self.population,
            'elevation': self.elevation,
            'dem': self.dem,
            'timezone': self.timezone,
            'moddate': self.moddate.strftime('%Y-%m-%d') if self.moddate else None,
            'related': {
                k: v.as_dict(related=False, alternate_titles=False)
                for (k, v) in self.related_geonames().items()
            }
            if related
            else {},
            'alternate_titles': [a.as_dict() for a in self.alternate_titles]
            if alternate_titles
            else [],
        }

    @classmethod
    def get(cls, name) -> GeoName | None:
        """Get geoname record matching given URL stub name."""
        return cls.query.filter_by(name=name).one_or_none()

    @classmethod
    def get_by_title(
        cls, titles: str | list[str], lang: str | None = None
    ) -> list[GeoName]:
        """
        Get geoname records matching the given titles.

        :param lang: Limit results to names in this language
        """
        results = set()
        if isinstance(titles, str):
            titles = [titles]
        for title in titles:
            if lang:
                results.update(
                    [
                        r.geoname
                        for r in GeoAltName.query.filter(
                            sa.func.lower(GeoAltName.title) == title.lower(),
                            GeoAltName.lang == lang,
                        ).all()
                        if r.geoname
                    ]
                )
            else:
                results.update(
                    [
                        r.geoname
                        for r in GeoAltName.query.filter(
                            sa.func.lower(GeoAltName.title) == title.lower()
                        ).all()
                        if r.geoname
                    ]
                )
        return sorted(
            results,
            key=lambda g: ({'A': 1, 'P': 2}.get(g.fclass or '', 0), g.population),
            reverse=True,
        )

    @classmethod
    def parse_locations(
        cls,
        q: str,
        special: list[str] | None = None,
        lang: str | None = None,
        bias: list[str] | None = None,
    ):
        """
        Parse a string and return annotations marking all identified locations.

        :param q: String to parse
        :param special: Special tokens to be marked in the annotations
        :param lang: Limit locations to names in this language
        :param bias: Country codes (ISO two letter) to prioritize locations from
        """
        special = [s.lower() for s in special] if special else []
        if bias is None:
            bias = []
        tokens = NOWORDS_RE.split(q)
        while '' in tokens:
            tokens.remove('')  # Remove blank tokens from beginning and end
        ltokens = [t.lower() for t in tokens]
        results: list[dict[str, object]] = []
        counter = 0
        limit = len(tokens)
        while counter < limit:
            token = tokens[counter]
            # Do a case-insensitive match
            ltoken = token.lower()
            # Ignore punctuation, only query for tokens containing text
            # Special-case 'or' and 'in' to prevent matching against Oregon and Indiana
            if ltoken not in ('or', 'in', 'to', 'the') and WORDS_RE.match(token):
                # Find a GeoAltName matching token, add GeoAltName.geoname to results
                if lang:
                    matches = (
                        GeoAltName.query.filter(
                            sa.func.lower(GeoAltName.title).like(ltoken)
                        )
                        .filter(
                            sa.or_(GeoAltName.lang == lang, GeoAltName.lang.is_(None))
                        )
                        .options(
                            sa_orm.joinedload(GeoAltName.geoname).joinedload(
                                GeoName.country
                            ),
                            sa_orm.joinedload(GeoAltName.geoname).joinedload(
                                GeoName.admin1code
                            ),
                            sa_orm.joinedload(GeoAltName.geoname).joinedload(
                                GeoName.admin2code
                            ),
                        )
                        .all()
                    )
                else:
                    matches = (
                        GeoAltName.query.filter(
                            sa.func.lower(GeoAltName.title).like(
                                quote_autocomplete_like(ltoken)
                            )
                        )
                        .options(
                            sa_orm.joinedload(GeoAltName.geoname).joinedload(
                                GeoName.country
                            ),
                            sa_orm.joinedload(GeoAltName.geoname).joinedload(
                                GeoName.admin1code
                            ),
                            sa_orm.joinedload(GeoAltName.geoname).joinedload(
                                GeoName.admin2code
                            ),
                        )
                        .all()
                    )
                if not matches:
                    # This token didn't match anything, move on
                    results.append({'token': token})
                else:
                    # Now filter through the matches to see if there are exact matches
                    candidates = [
                        (NOWORDS_RE.split(m.title.lower()), m) for m in matches
                    ]
                    fullmatch = []
                    for mtokens, match in candidates:
                        if mtokens == ltokens[counter : counter + len(mtokens)]:
                            fullmatch.append((len(mtokens), match))
                    if fullmatch:
                        maxmatch = max(f[0] for f in fullmatch)
                        accepted = list({f[1] for f in fullmatch if f[0] == maxmatch})
                        # Filter accepted down to one match.
                        # Sort by (a) bias, (b) language match, (c) city over state and
                        # (d) population
                        accepted.sort(
                            key=lambda a: (
                                {
                                    v: k
                                    for k, v in enumerate(
                                        reversed(cast(list[str], bias))
                                    )
                                }.get(a.geoname.country_id, -1),
                                {lang: 0}.get(a.lang, 1),
                                {'A': 1, 'P': 2}.get(a.geoname.fclass, 0),
                                a.geoname.population,
                            ),
                            reverse=True,
                        )
                        results.append(
                            {
                                'token': ''.join(tokens[counter : counter + maxmatch]),
                                'geoname': accepted[0].geoname,
                            }
                        )
                        counter += maxmatch - 1
                    else:
                        results.append({'token': token})
            else:
                results.append({'token': token})

            if ltoken in special:
                results[-1]['special'] = True
            counter += 1
        return results

    @classmethod
    def autocomplete(cls, prefix: str, lang: str | None = None) -> Query[Self]:
        """
        Autocomplete a geoname record.

        :param q: Partial title to complete
        :param lang: Limit results to names in this language
        """
        query = (
            cls.query.join(cls.alternate_titles)
            .filter(
                sa.func.lower(GeoAltName.title).like(
                    quote_autocomplete_like(prefix.lower())
                )
            )
            .order_by(sa.desc(cls.population))
        )
        if lang:
            query = query.filter(
                sa.or_(GeoAltName.lang.is_(None), GeoAltName.lang == lang)
            )
        return query


class GeoAltName(BaseMixin, GeonameModel):
    """Additional names for any :class:`GeoName`."""

    __tablename__ = 'geo_alt_name'

    geonameid: Mapped[int] = sa_orm.mapped_column(
        sa.Integer, sa.ForeignKey('geo_name.id'), nullable=False
    )
    geoname: Mapped[GeoName] = relationship(back_populates='alternate_titles')
    lang: Mapped[str | None] = sa_orm.mapped_column(
        sa.Unicode, nullable=True, index=True
    )
    title: Mapped[str] = sa_orm.mapped_column(sa.Unicode, nullable=False)
    is_preferred_name: Mapped[str] = sa_orm.mapped_column(sa.Boolean, nullable=False)
    is_short_name: Mapped[bool] = sa_orm.mapped_column(sa.Boolean, nullable=False)
    is_colloquial: Mapped[bool] = sa_orm.mapped_column(sa.Boolean, nullable=False)
    is_historic: Mapped[bool] = sa_orm.mapped_column(sa.Boolean, nullable=False)

    __table_args__ = (
        sa.Index(
            'ix_geo_alt_name_title',
            sa.func.lower('title').label('title_lower'),
            postgresql_ops={'title_lower': 'varchar_pattern_ops'},
        ),
    )

    def __repr__(self) -> str:
        """Return representation."""
        return f'<GeoAltName {self.lang} "{self.title}" of {self.geoname!r}>'

    def as_dict(self) -> dict:
        """Convert this record into a dictionary suitable for casting to JSON."""
        return {
            'geonameid': self.geonameid,
            'lang': self.lang,
            'title': self.title,
            'is_preferred_name': self.is_preferred_name,
            'is_short_name': self.is_short_name,
            'is_colloquial': self.is_colloquial,
            'is_historic': self.is_historic,
        }
