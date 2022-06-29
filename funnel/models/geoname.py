"""Geoname data models."""

from __future__ import annotations

from typing import Collection, Dict, List, Optional, Union, cast
import re

from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import joinedload

from coaster.sqlalchemy import Query
from coaster.utils import make_name

from . import BaseMixin, BaseNameMixin, db
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


class GeoCountryInfo(BaseNameMixin, db.Model):
    """Geoname record for a country."""

    __tablename__ = 'geo_country_info'
    __bind_key__ = 'geoname'

    geonameid = db.synonym('id')
    geoname = db.relationship(
        'GeoName',
        uselist=False,
        primaryjoin='GeoCountryInfo.id == foreign(GeoName.id)',
        backref='has_country',
    )
    iso_alpha2 = db.Column(db.CHAR(2), unique=True)
    iso_alpha3 = db.Column(db.CHAR(3), unique=True)
    iso_numeric = db.Column(db.Integer)
    fips_code = db.Column(db.Unicode(3))
    capital = db.Column(db.Unicode)
    area_in_sqkm = db.Column(db.Numeric)
    population = db.Column(db.BigInteger)
    continent = db.Column(db.CHAR(2))
    tld = db.Column(db.Unicode(3))
    currency_code = db.Column(db.CHAR(3))
    currency_name = db.Column(db.Unicode)
    phone = db.Column(db.Unicode(16))
    postal_code_format = db.Column(db.Unicode)
    postal_code_regex = db.Column(db.Unicode)
    languages = db.Column(ARRAY(db.Unicode, dimensions=1))
    neighbours = db.Column(ARRAY(db.CHAR(2), dimensions=1))
    equivalent_fips_code = db.Column(db.Unicode(3))

    __table_args__ = (
        db.Index(
            'ix_geo_country_info_title',
            db.func.lower('title').label('title_lower'),
            postgresql_ops={'title_lower': 'varchar_pattern_ops'},
        ),
    )

    def __repr__(self):
        """Return representation."""
        return f'<GeoCountryInfo {self.geonameid} "{self.title}">'


class GeoAdmin1Code(BaseMixin, db.Model):
    """Geoname record for 1st level administrative division (state, province)."""

    __tablename__ = 'geo_admin1_code'
    __bind_key__ = 'geoname'

    geonameid = db.synonym('id')
    geoname = db.relationship(
        'GeoName',
        uselist=False,
        primaryjoin='GeoAdmin1Code.id == foreign(GeoName.id)',
        backref='has_admin1code',
        viewonly=True,
    )
    title = db.Column(db.Unicode)
    ascii_title = db.Column(db.Unicode)
    country_id = db.Column(
        'country', db.CHAR(2), db.ForeignKey('geo_country_info.iso_alpha2')
    )
    country = db.relationship('GeoCountryInfo')
    admin1_code = db.Column(db.Unicode)

    def __repr__(self):
        """Return representation."""
        return f'<GeoAdmin1Code {self.geonameid} "self.ascii_title">'


class GeoAdmin2Code(BaseMixin, db.Model):
    """Geoname record for 2nd level administrative division (disrict, county)."""

    __tablename__ = 'geo_admin2_code'
    __bind_key__ = 'geoname'

    geonameid = db.synonym('id')
    geoname = db.relationship(
        'GeoName',
        uselist=False,
        primaryjoin='GeoAdmin2Code.id == foreign(GeoName.id)',
        backref='has_admin2code',
        viewonly=True,
    )
    title = db.Column(db.Unicode)
    ascii_title = db.Column(db.Unicode)
    country_id = db.Column(
        'country', db.CHAR(2), db.ForeignKey('geo_country_info.iso_alpha2')
    )
    country = db.relationship('GeoCountryInfo')
    admin1_code = db.Column(db.Unicode)
    admin2_code = db.Column(db.Unicode)

    def __repr__(self):
        """Return representation."""
        return f'<GeoAdmin2Code {self.geonameid} "self.ascii_title">'


class GeoName(BaseNameMixin, db.Model):
    """Geographical name record."""

    __tablename__ = 'geo_name'
    __bind_key__ = 'geoname'

    geonameid = db.synonym('id')
    ascii_title = db.Column(db.Unicode)
    latitude = db.Column(db.Numeric)
    longitude = db.Column(db.Numeric)
    fclass = db.Column(db.CHAR(1))
    fcode = db.Column(db.Unicode)
    country_id = db.Column(
        'country', db.CHAR(2), db.ForeignKey('geo_country_info.iso_alpha2')
    )
    country = db.relationship('GeoCountryInfo')
    cc2 = db.Column(db.Unicode)
    admin1 = db.Column(db.Unicode)
    admin1_ref = db.relationship(
        'GeoAdmin1Code',
        uselist=False,
        primaryjoin='and_(GeoName.country_id == foreign(GeoAdmin1Code.country_id), '
        'GeoName.admin1 == foreign(GeoAdmin1Code.admin1_code))',
        viewonly=True,
    )
    admin1_id = db.Column(None, db.ForeignKey('geo_admin1_code.id'), nullable=True)
    admin1code = db.relationship(
        'GeoAdmin1Code', uselist=False, foreign_keys=[admin1_id]
    )

    admin2 = db.Column(db.Unicode)
    admin2_ref = db.relationship(
        'GeoAdmin2Code',
        uselist=False,
        primaryjoin='and_(GeoName.country_id == foreign(GeoAdmin2Code.country_id), '
        'GeoName.admin1 == foreign(GeoAdmin2Code.admin1_code), '
        'GeoName.admin2 == foreign(GeoAdmin2Code.admin2_code))',
        viewonly=True,
    )
    admin2_id = db.Column(None, db.ForeignKey('geo_admin2_code.id'), nullable=True)
    admin2code = db.relationship(
        'GeoAdmin2Code', uselist=False, foreign_keys=[admin2_id]
    )

    admin4 = db.Column(db.Unicode)
    admin3 = db.Column(db.Unicode)
    population = db.Column(db.BigInteger)
    elevation = db.Column(db.Integer)
    dem = db.Column(db.Integer)  # Digital Elevation Model
    timezone = db.Column(db.Unicode)
    moddate = db.Column(db.Date)

    __table_args__ = (
        db.Index(
            'ix_geo_name_title',
            db.func.lower('title').label('title_lower'),
            postgresql_ops={'title_lower': 'varchar_pattern_ops'},
        ),
        db.Index(
            'ix_geo_name_ascii_title',
            db.func.lower(ascii_title).label('ascii_title_lower'),
            postgresql_ops={'ascii_title_lower': 'varchar_pattern_ops'},
        ),
    )

    @property
    def short_title(self) -> str:
        """Return a short title for this geoname record."""
        if self.has_country:
            return self.has_country.title
        if self.has_admin1code:
            return self.admin1code.title if self.admin1code else self.admin1_ref.title
        if self.has_admin2code:
            return self.admin2code.title if self.admin2code else self.admin2_ref.title
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
        usetitle = self.ascii_title
        if self.fclass == 'A' and self.fcode.startswith('PCL'):
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
            if self.id:

                def checkused(c):
                    return bool(
                        c in reserved
                        or GeoName.query.filter(GeoName.id != self.id)
                        .filter_by(name=c)
                        .notempty()
                    )

            else:

                def checkused(c):
                    return bool(
                        c in reserved or GeoName.query.filter_by(name=c).notempty()
                    )

            with db.session.no_autoflush:
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
        if (self.fclass, self.fcode) != ('L', 'CONT') and self.country:
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
                            db.func.lower(GeoAltName.title) == title.lower(),
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
                            db.func.lower(GeoAltName.title) == title.lower()
                        ).all()
                        if r.geoname
                    ]
                )
        return sorted(
            results,
            key=lambda g: ({'A': 1, 'P': 2}.get(g.fclass, 0), g.population),
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
                            db.func.lower(GeoAltName.title).like(ltoken)
                        )
                        .filter(
                            db.or_(GeoAltName.lang == lang, GeoAltName.lang.is_(None))
                        )
                        .options(
                            joinedload('geoname').joinedload('country'),
                            joinedload('geoname').joinedload('admin1code'),
                            joinedload('geoname').joinedload('admin2code'),
                        )
                        .all()
                    )
                else:
                    matches = (
                        GeoAltName.query.filter(
                            db.func.lower(GeoAltName.title).like(
                                quote_autocomplete_like(ltoken)
                            )
                        )
                        .options(
                            joinedload('geoname').joinedload('country'),
                            joinedload('geoname').joinedload('admin1code'),
                            joinedload('geoname').joinedload('admin2code'),
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
    def autocomplete(cls, q: str, lang: Optional[str] = None) -> Query:
        """
        Autocomplete a geoname record.

        :param q: Partial title to complete
        :param lang: Limit results to names in this language
        """
        query = (
            cls.query.join(cls.alternate_titles)
            .filter(
                db.func.lower(GeoAltName.title).like(quote_autocomplete_like(q.lower()))
            )
            .order_by(db.desc(cls.population))
        )
        if lang:
            query = query.filter(
                db.or_(GeoAltName.lang.is_(None), GeoAltName.lang == lang)
            )
        return query


class GeoAltName(BaseMixin, db.Model):
    """Additional names for any :class:`GeoName`."""

    __tablename__ = 'geo_alt_name'
    __bind_key__ = 'geoname'

    geonameid = db.Column(None, db.ForeignKey('geo_name.id'), nullable=False)
    geoname = db.relationship(
        GeoName, backref=db.backref('alternate_titles', cascade='all, delete-orphan')
    )
    lang = db.Column(db.Unicode, nullable=True, index=True)
    title = db.Column(db.Unicode, nullable=False)
    is_preferred_name = db.Column(db.Boolean, nullable=False)
    is_short_name = db.Column(db.Boolean, nullable=False)
    is_colloquial = db.Column(db.Boolean, nullable=False)
    is_historic = db.Column(db.Boolean, nullable=False)

    __table_args__ = (
        db.Index(
            'ix_geo_alt_name_title',
            db.func.lower('title').label('title_lower'),
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
