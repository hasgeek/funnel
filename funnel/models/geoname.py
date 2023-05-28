"""Geoname data models."""

from __future__ import annotations

from typing import Collection, Dict, List, Optional, Union, cast
import re

from sqlalchemy.dialects.postgresql import ARRAY

from coaster.utils import make_name

from . import BaseMixin, BaseNameMixin, Mapped, Query, db, sa
from .helpers import quote_autocomplete_like

__all__ = ['GeoName', 'GeoCountryInfo', 'GeoAdmin1Code', 'GeoAdmin2Code', 'GeoAltName']


NOWORDS_RE = re.compile(r'(\W+)', re.UNICODE)
WORDS_RE = re.compile(r'\w+', re.UNICODE)

continent_codes = {
    'AF': 6255146,  # Africa
    'AS': 6255147,  # Asia
    'EU': 6255148,  # Europe
    'NA': 6255149,  # North America
    'OC': 6255151,  # Ocenia
    'SA': 6255150,  # South America
    'AN': 6255152,  # Antarctica
}


class GeoCountryInfo(BaseNameMixin, db.Model):  # type: ignore[name-defined]
    """Geoname record for a country."""

    __tablename__ = 'geo_country_info'
    __allow_unmapped__ = True
    __bind_key__ = 'geoname'

    geonameid: Mapped[int] = sa.orm.synonym('id')
    geoname: Mapped[GeoName] = sa.orm.relationship(
        'GeoName',
        uselist=False,
        primaryjoin='GeoCountryInfo.id == foreign(GeoName.id)',
        backref='has_country',
    )
    iso_alpha2 = sa.Column(sa.CHAR(2), unique=True)
    iso_alpha3 = sa.Column(sa.CHAR(3), unique=True)
    iso_numeric = sa.Column(sa.Integer)
    fips_code = sa.Column(sa.Unicode(3))
    capital = sa.Column(sa.Unicode)
    area_in_sqkm = sa.Column(sa.Numeric)
    population = sa.Column(sa.BigInteger)
    continent = sa.Column(sa.CHAR(2))
    tld = sa.Column(sa.Unicode(3))
    currency_code = sa.Column(sa.CHAR(3))
    currency_name = sa.Column(sa.Unicode)
    phone = sa.Column(sa.Unicode(16))
    postal_code_format = sa.Column(sa.Unicode)
    postal_code_regex = sa.Column(sa.Unicode)
    languages = sa.Column(ARRAY(sa.Unicode, dimensions=1))
    neighbours = sa.Column(ARRAY(sa.CHAR(2), dimensions=1))
    equivalent_fips_code = sa.Column(sa.Unicode(3))

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


class GeoAdmin1Code(BaseMixin, db.Model):  # type: ignore[name-defined]
    """Geoname record for 1st level administrative division (state, province)."""

    __tablename__ = 'geo_admin1_code'
    __allow_unmapped__ = True
    __bind_key__ = 'geoname'

    geonameid: Mapped[int] = sa.orm.synonym('id')
    geoname: Mapped[GeoName] = sa.orm.relationship(
        'GeoName',
        uselist=False,
        primaryjoin='GeoAdmin1Code.id == foreign(GeoName.id)',
        backref='has_admin1code',
        viewonly=True,
    )
    title = sa.Column(sa.Unicode)
    ascii_title = sa.Column(sa.Unicode)
    country_id = sa.Column(
        'country', sa.CHAR(2), sa.ForeignKey('geo_country_info.iso_alpha2')
    )
    country: Mapped[GeoCountryInfo] = sa.orm.relationship('GeoCountryInfo')
    admin1_code = sa.Column(sa.Unicode)

    def __repr__(self) -> str:
        """Return representation."""
        return f'<GeoAdmin1Code {self.geonameid} "self.ascii_title">'


class GeoAdmin2Code(BaseMixin, db.Model):  # type: ignore[name-defined]
    """Geoname record for 2nd level administrative division (district, county)."""

    __tablename__ = 'geo_admin2_code'
    __allow_unmapped__ = True
    __bind_key__ = 'geoname'

    geonameid: Mapped[int] = sa.orm.synonym('id')
    geoname: Mapped[GeoName] = sa.orm.relationship(
        'GeoName',
        uselist=False,
        primaryjoin='GeoAdmin2Code.id == foreign(GeoName.id)',
        backref='has_admin2code',
        viewonly=True,
    )
    title = sa.Column(sa.Unicode)
    ascii_title = sa.Column(sa.Unicode)
    country_id = sa.Column(
        'country', sa.CHAR(2), sa.ForeignKey('geo_country_info.iso_alpha2')
    )
    country: Mapped[GeoCountryInfo] = sa.orm.relationship('GeoCountryInfo')
    admin1_code = sa.Column(sa.Unicode)
    admin2_code = sa.Column(sa.Unicode)

    def __repr__(self) -> str:
        """Return representation."""
        return f'<GeoAdmin2Code {self.geonameid} "self.ascii_title">'


class GeoName(BaseNameMixin, db.Model):  # type: ignore[name-defined]
    """Geographical name record."""

    __tablename__ = 'geo_name'
    __allow_unmapped__ = True
    __bind_key__ = 'geoname'

    geonameid: Mapped[int] = sa.orm.synonym('id')
    ascii_title = sa.Column(sa.Unicode)
    latitude = sa.Column(sa.Numeric)
    longitude = sa.Column(sa.Numeric)
    fclass = sa.Column(sa.CHAR(1))
    fcode = sa.Column(sa.Unicode)
    country_id = sa.Column(
        'country', sa.CHAR(2), sa.ForeignKey('geo_country_info.iso_alpha2')
    )
    country: Mapped[GeoCountryInfo] = sa.orm.relationship('GeoCountryInfo')
    cc2 = sa.Column(sa.Unicode)
    admin1 = sa.Column(sa.Unicode)
    admin1_ref: Mapped[Optional[GeoAdmin1Code]] = sa.orm.relationship(
        'GeoAdmin1Code',
        uselist=False,
        primaryjoin='and_(GeoName.country_id == foreign(GeoAdmin1Code.country_id), '
        'GeoName.admin1 == foreign(GeoAdmin1Code.admin1_code))',
        viewonly=True,
    )
    admin1_id = sa.Column(
        sa.Integer, sa.ForeignKey('geo_admin1_code.id'), nullable=True
    )
    admin1code: Mapped[Optional[GeoAdmin1Code]] = sa.orm.relationship(
        'GeoAdmin1Code', uselist=False, foreign_keys=[admin1_id]
    )

    admin2 = sa.Column(sa.Unicode)
    admin2_ref: Mapped[Optional[GeoAdmin2Code]] = sa.orm.relationship(
        'GeoAdmin2Code',
        uselist=False,
        primaryjoin='and_(GeoName.country_id == foreign(GeoAdmin2Code.country_id), '
        'GeoName.admin1 == foreign(GeoAdmin2Code.admin1_code), '
        'GeoName.admin2 == foreign(GeoAdmin2Code.admin2_code))',
        viewonly=True,
    )
    admin2_id = sa.Column(
        sa.Integer, sa.ForeignKey('geo_admin2_code.id'), nullable=True
    )
    admin2code: Mapped[Optional[GeoAdmin2Code]] = sa.orm.relationship(
        'GeoAdmin2Code', uselist=False, foreign_keys=[admin2_id]
    )

    admin4 = sa.Column(sa.Unicode)
    admin3 = sa.Column(sa.Unicode)
    population = sa.Column(sa.BigInteger)
    elevation = sa.Column(sa.Integer)
    dem = sa.Column(sa.Integer)  # Digital Elevation Model
    timezone = sa.Column(sa.Unicode)
    moddate = sa.Column(sa.Date)

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
                self.admin1code.title if self.admin1code else self.admin1_ref.title
            ) or ''
        if self.has_admin2code:
            return (
                self.admin2code.title if self.admin2code else self.admin2_ref.title
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
        """Return a recommended usable title."""
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

    def related_geonames(self) -> Dict[str, GeoName]:
        """Return related geonames based on superior hierarchy (country, state, etc)."""
        related = {}
        if self.admin2code and self.admin2code.geonameid != self.geonameid:
            related['admin2'] = self.admin2code.geoname
        if self.admin1code and self.admin1code.geonameid != self.geonameid:
            related['admin1'] = self.admin1code.geoname
        if self.country and self.country.geonameid != self.geonameid:
            related['country'] = self.country.geoname
        if (
            (self.fclass, self.fcode) != ('L', 'CONT')
            and self.country
            and self.country.continent
        ):
            related['continent'] = GeoName.query.get(
                continent_codes[self.country.continent]
            )
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
    def get(cls, name) -> Optional[GeoName]:
        """Get geoname record matching given URL stub name."""
        return cls.query.filter_by(name=name).one_or_none()

    @classmethod
    def get_by_title(
        cls, titles: Union[str, List[str]], lang: Optional[str] = None
    ) -> List[GeoName]:
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
        special: Optional[List[str]] = None,
        lang: Optional[str] = None,
        bias: Optional[List[str]] = None,
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
        results: List[Dict[str, object]] = []
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
                            sa.orm.joinedload(GeoAltName.geoname).joinedload(
                                GeoName.country
                            ),
                            sa.orm.joinedload(GeoAltName.geoname).joinedload(
                                GeoName.admin1code
                            ),
                            sa.orm.joinedload(GeoAltName.geoname).joinedload(
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
                            sa.orm.joinedload(GeoAltName.geoname).joinedload(
                                GeoName.country
                            ),
                            sa.orm.joinedload(GeoAltName.geoname).joinedload(
                                GeoName.admin1code
                            ),
                            sa.orm.joinedload(GeoAltName.geoname).joinedload(
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
                                        reversed(cast(List[str], bias))
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
    def autocomplete(cls, prefix: str, lang: Optional[str] = None) -> Query[GeoName]:
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


class GeoAltName(BaseMixin, db.Model):  # type: ignore[name-defined]
    """Additional names for any :class:`GeoName`."""

    __tablename__ = 'geo_alt_name'
    __allow_unmapped__ = True
    __bind_key__ = 'geoname'

    geonameid = sa.Column(sa.Integer, sa.ForeignKey('geo_name.id'), nullable=False)
    geoname: Mapped[GeoName] = sa.orm.relationship(
        GeoName,
        backref=sa.orm.backref('alternate_titles', cascade='all, delete-orphan'),
    )
    lang = sa.Column(sa.Unicode, nullable=True, index=True)
    title = sa.Column(sa.Unicode, nullable=False)
    is_preferred_name = sa.Column(sa.Boolean, nullable=False)
    is_short_name = sa.Column(sa.Boolean, nullable=False)
    is_colloquial = sa.Column(sa.Boolean, nullable=False)
    is_historic = sa.Column(sa.Boolean, nullable=False)

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
