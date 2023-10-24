"""API views for geoname data."""

from __future__ import annotations

from coaster.utils import getbool
from coaster.views import requestargs

from ... import app
from ...models import GeoName
from ...typing import ReturnRenderWith


@app.route('/api/1/geo/get_by_name')
@requestargs('name', ('related', getbool), ('alternate_titles', getbool))
def geo_get_by_name(
    name: str, related: bool = False, alternate_titles: bool = False
) -> ReturnRenderWith:
    """Get a geoname record given a single URL stub name or geoname id."""
    if name.isdigit():
        geoname = GeoName.query.get(int(name))
    else:
        geoname = GeoName.get(name)
    return (
        {
            'status': 'ok',
            'result': geoname.as_dict(
                related=related, alternate_titles=alternate_titles
            ),
        }
        if geoname
        else {'status': 'error', 'error': 'not_found'}
    )


@app.route('/api/1/geo/get_by_names')
@requestargs('name[]', ('related', getbool), ('alternate_titles', getbool))
def geo_get_by_names(
    name: list[str], related: bool = False, alternate_titles: bool = False
) -> ReturnRenderWith:
    """Get geoname records matching given URL stub names or geonameids."""
    geonames = []
    for n in name:
        if n.isdigit():
            geoname = GeoName.query.get(int(n))
        else:
            geoname = GeoName.get(n)
        if geoname:
            geonames.append(geoname)
    return {
        'status': 'ok',
        'result': [
            gn.as_dict(related=related, alternate_titles=alternate_titles)
            for gn in geonames
        ],
    }


@app.route('/api/1/geo/get_by_title')
@requestargs('title[]', 'lang')
def geo_get_by_title(title: list[str], lang: str | None = None) -> ReturnRenderWith:
    """Get locations matching given titles."""
    return {
        'status': 'ok',
        'result': [g.as_dict() for g in GeoName.get_by_title(title, lang)],
    }


@app.route('/api/1/geo/parse_locations')
@requestargs('q', 'special[]', 'lang', 'bias[]', ('alternate_titles', getbool))
def geo_parse_location(
    q: str,
    special: list[str] | None = None,
    lang: str | None = None,
    bias: list[str] | None = None,
    alternate_titles: bool = False,
) -> ReturnRenderWith:
    """Parse locations from a string of locations."""
    result = GeoName.parse_locations(q, special, lang, bias)
    for item in result:
        if 'geoname' in item:
            item['geoname'] = item['geoname'].as_dict(alternate_titles=alternate_titles)
    return {'status': 'ok', 'result': result}


@app.route('/api/1/geo/autocomplete')
@requestargs('q', 'lang', ('limit', int))
def geo_autocomplete(
    q: str, lang: str | None = None, limit: int = 100
) -> ReturnRenderWith:
    """Autocomplete a geoname record."""
    return {
        'status': 'ok',
        'result': [
            g.as_dict(related=False, alternate_titles=False)
            for g in GeoName.autocomplete(q, lang).limit(limit)
        ],
    }
