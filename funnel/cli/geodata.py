"""Process geonames data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from urllib.parse import urljoin
import csv
import os
import sys
import time
import zipfile

from flask.cli import AppGroup
import click

from unidecode import unidecode
import requests
import rich.progress

from coaster.utils import getbool

from .. import app
from ..models import (
    GeoAdmin1Code,
    GeoAdmin2Code,
    GeoAltName,
    GeoCountryInfo,
    GeoName,
    db,
)

csv.field_size_limit(sys.maxsize)

geo = AppGroup('geoname', help="Process geoname data.")


@dataclass
class CountryInfoRecord:
    """Geonames country info record."""

    iso_alpha2: str
    iso_alpha3: str
    iso_numeric: str
    fips_code: str
    title: str
    capital: str
    area_in_sqkm: str
    population: str
    continent: str
    tld: str
    currency_code: str
    currency_name: str
    phone: str
    postal_code_format: str
    postal_code_regex: str
    languages: str
    geonameid: str
    neighbours: str
    equivalent_fips_code: str


@dataclass
class GeoNameRecord:
    """Geonames name record."""

    geonameid: str
    title: str
    ascii_title: str
    alternatenames: str
    latitude: str
    longitude: str
    fclass: str
    fcode: str
    country_id: str
    cc2: str
    admin1: str
    admin2: str
    admin3: str
    admin4: str
    population: str
    elevation: str
    dem: str
    timezone: str
    moddate: str


@dataclass
class GeoAdminRecord:
    """Geonames admin record."""

    code: str
    title: str
    ascii_title: str
    geonameid: str


@dataclass
class GeoAltNameRecord:
    """Geonames alt name record."""

    id: str  # noqa: A003
    geonameid: str
    lang: str
    title: str
    is_preferred_name: str
    is_short_name: str
    is_colloquial: str
    is_historic: str


def downloadfile(basepath: str, filename: str, folder: Optional[str] = None) -> None:
    """Download a geoname record file."""
    if not folder:
        folder_file = filename
    else:
        folder_file = os.path.join(folder, filename)
    if (
        os.path.exists(folder_file)
        and (time.time() - os.path.getmtime(folder_file)) < 86400
    ):
        click.echo(f"Skipping re-download of recent {filename}")
        return
    with rich.progress.Progress(
        rich.progress.TextColumn('{task.description}'),
        rich.progress.BarColumn(),
        "[progress.percentage]{task.percentage:>3.1f}%",
        rich.progress.DownloadColumn(),
        rich.progress.TransferSpeedColumn(),
        rich.progress.TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task(f"Downloading {filename}", total=None)
        url = urljoin(basepath, filename)
        r = requests.get(url, stream=True, timeout=30)
        if r.status_code == 200:
            filesize = int(r.headers.get('content-length', 0))
            if filesize:
                progress.update(task, total=filesize)
            with open(folder_file, 'wb') as fd:
                for chunk in r.iter_content(1024):
                    if not chunk:
                        # Break when done. The connection remains open for Keep-Alive
                        break
                    fd.write(chunk)
                    progress.update(task, advance=len(chunk))

        if filename.lower().endswith('.zip'):
            with zipfile.ZipFile(folder_file, 'r') as zipf:
                zipf.extractall(folder)


def load_country_info(filename: str) -> None:
    """Load country geonames from the given file descriptor."""
    with rich.progress.open(
        filename,
        mode='rt',
        newline='',
        encoding='utf-8',
        description="Loading country info...",
    ) as fd:
        countryinfo = [
            CountryInfoRecord(*row)
            for row in csv.reader(fd, delimiter='\t')
            if not row[0].startswith('#')
        ]

        GeoCountryInfo.query.all()  # Load everything into session cache
        for item in countryinfo:
            if item.geonameid:
                ci = GeoCountryInfo.query.get(int(item.geonameid))
                if ci is None:
                    ci = GeoCountryInfo(geonameid=int(item.geonameid))
                    db.session.add(ci)

                ci.iso_alpha2 = item.iso_alpha2
                ci.iso_alpha3 = item.iso_alpha3
                ci.iso_numeric = int(item.iso_numeric)
                ci.fips_code = item.fips_code
                ci.title = item.title
                ci.capital = item.capital
                ci.area_in_sqkm = (
                    Decimal(item.area_in_sqkm) if item.area_in_sqkm else None
                )
                ci.population = int(item.population)
                ci.continent = item.continent
                ci.tld = item.tld
                ci.currency_code = item.currency_code
                ci.currency_name = item.currency_name
                ci.phone = item.phone
                ci.postal_code_format = item.postal_code_format
                ci.postal_code_regex = item.postal_code_regex
                ci.languages = item.languages.split(',')
                ci.neighbours = item.neighbours.split(',')
                ci.equivalent_fips_code = item.equivalent_fips_code

                ci.make_name()

        db.session.commit()


def load_geonames(filename: str) -> None:
    """Load geonames matching fixed criteria from the given file descriptor."""
    geonames = []

    # Feature descriptions: http://download.geonames.org/export/dump/featureCodes_en.txt
    # Sorting order, larger number has more weight
    loadfeatures = {
        ('L', 'CONT'): 22,  # Continent
        ('A', 'PCL'): 21,  # Political entity (country)
        ('A', 'PCLD'): 20,  # Dependent political entity
        ('A', 'PCLF'): 19,  # Freely associated state
        ('A', 'PCLI'): 18,  # Independent political entity
        ('A', 'PCLS'): 17,  # Semi-independent political entity
        ('A', 'ADM1'): 16,  # First-order administrative division (state, province)
        ('P', 'PPLC'): 15,  # capital of a political entity
        ('P', 'PPLA'): 14,  # Seat of a first-order admin. division (state capital)
        ('P', 'PPLA2'): 13,  # Seat of a second-order administrative division
        ('P', 'PPLA3'): 12,  # Seat of a third-order administrative division
        ('P', 'PPLA4'): 11,  # Seat of a fourth-order administrative division
        ('P', 'PPLG'): 10,  # Seat of government of a political entity
        ('P', 'PPL'): 9,  # Populated place (city, could be a neighbourhood too)
        ('P', 'PPLR'): 8,  # Religious populated place
        ('P', 'PPLS'): 7,  # Populated places
        ('P', 'PPLX'): 6,  # Section of populated place
        ('S', 'TRIG'): 5,  # Triangulated location (shows up in data instead of P.PPL)
        ('P', 'PPLL'): 4,  # Populated locality
        ('P', 'PPLF'): 3,  # Farm village
        ('A', 'ADM2'): 2,  # Second-order administrative division (district, county)
        ('A', 'ADM3'): 1,  # Third-order administrative division
    }

    with rich.progress.open(
        filename,
        mode='rt',
        newline='',
        encoding='utf-8',
        description=f"Loading geonames from {filename}...",
    ) as fd:
        for line in fd:
            if not line.startswith('#'):
                rec = GeoNameRecord(*line.strip().split('\t'))
                # Ignore places that have a population below 15,000, but keep places
                # that have a population of 0, since that indicates data wasn't
                # available
                if rec.fclass == 'P' and (
                    (
                        rec.population.isdigit()
                        and int(rec.population != 0)
                        and int(rec.population) < 15000
                    )
                    or not rec.population.isdigit()
                ):
                    continue
                if (rec.fclass, rec.fcode) not in loadfeatures:
                    continue
                geonames.append(rec)

    click.echo(f"Sorting {len(geonames)} records...")

    geonames = [
        row[3]
        for row in sorted(
            (
                (
                    loadfeatures[(item.fclass, item.fcode)],
                    int(item.population) if item.population else 0,
                    int(item.geonameid) if item.geonameid.isdigit() else item.geonameid,
                    item,
                )
                for item in geonames
            ),
            reverse=True,
        )
    ]
    GeoName.query.all()  # Load all data into session cache for faster lookup

    for item in rich.progress.track(geonames):
        if item.geonameid:
            gn = GeoName.query.get(int(item.geonameid))
            if gn is None:
                gn = GeoName(geonameid=int(item.geonameid))
                db.session.add(gn)

            gn.title = item.title or ''
            gn.ascii_title = item.ascii_title or unidecode(item.title or '').replace(
                '@', 'a'
            )
            gn.latitude = Decimal(item.latitude) or None
            gn.longitude = Decimal(item.longitude) or None
            gn.fclass = item.fclass or None
            gn.fcode = item.fcode or None
            gn.country_id = item.country_id or None
            gn.cc2 = item.cc2 or None
            gn.admin1 = item.admin1 or None
            gn.admin2 = item.admin2 or None
            gn.admin3 = item.admin3 or None
            gn.admin4 = item.admin4 or None
            gn.admin1code = gn.admin1_ref
            gn.admin2code = gn.admin2_ref
            gn.population = int(item.population) if item.population else None
            gn.elevation = int(item.elevation) if item.elevation else None
            gn.dem = int(item.dem) if item.dem else None
            gn.timezone = item.timezone or None
            gn.moddate = (
                datetime.strptime(item.moddate, '%Y-%m-%d').date()
                if item.moddate
                else None
            )

            gn.make_name()
            # Required for future make_name() calls to work correctly
            db.session.flush()

    db.session.commit()


def load_alt_names(filename: str) -> None:
    """Load alternative names for geonames from the given file descriptor."""
    click.echo("Retrieving all geoname records...")
    geonameids = {r[0] for r in db.session.query(GeoName.id).all()}
    with rich.progress.open(
        filename,
        mode='rt',
        newline='',
        encoding='utf-8',
        description="Loading alternate names...",
    ) as fd:
        altnames = [
            GeoAltNameRecord(*row)
            for counter, row in enumerate(csv.reader(fd, delimiter='\t'))
            if not row[0].startswith('#') and int(row[1]) in geonameids
        ]

    GeoAltName.query.all()  # Load all data into session cache for faster lookup

    for item in rich.progress.track(altnames):
        if item.geonameid:
            rec = GeoAltName.query.get(int(item.id))
            if rec is None:
                rec = GeoAltName(id=int(item.id))
                db.session.add(rec)
            rec.geonameid = int(item.geonameid)
            rec.lang = item.lang or None
            rec.title = item.title
            rec.is_preferred_name = getbool(item.is_preferred_name) or False
            rec.is_short_name = getbool(item.is_short_name) or False
            rec.is_colloquial = getbool(item.is_colloquial) or False
            rec.is_historic = getbool(item.is_historic) or False

    db.session.commit()


def load_admin1_codes(filename: str) -> None:
    """Load admin1 codes from the given file descriptor."""
    with rich.progress.open(
        filename,
        mode='rt',
        newline='',
        encoding='utf-8',
        description="Loading admin1 codes...",
    ) as fd:
        admincodes = [
            GeoAdminRecord(*row)
            for row in csv.reader(fd, delimiter='\t')
            if not row[0].startswith('#')
        ]

    GeoAdmin1Code.query.all()  # Load all data into session cache for faster lookup
    for item in rich.progress.track(admincodes):
        if item.geonameid:
            rec = GeoAdmin1Code.query.get(item.geonameid)
            if rec is None:
                rec = GeoAdmin1Code(geonameid=item.geonameid)
                db.session.add(rec)
            rec.title = item.title
            rec.ascii_title = item.ascii_title
            rec.country_id, rec.admin1_code = item.code.split('.')

    db.session.commit()


def load_admin2_codes(filename: str) -> None:
    """Load admin2 codes from the given file descriptor."""
    with rich.progress.open(
        filename,
        mode='rt',
        newline='',
        encoding='utf-8',
        description="Loading admin2 codes...",
    ) as fd:
        admincodes = [
            GeoAdminRecord(*row)
            for row in csv.reader(fd, delimiter='\t')
            if not row[0].startswith('#')
        ]

    GeoAdmin2Code.query.all()  # Load all data into session cache for faster lookup
    for item in rich.progress.track(admincodes):
        if item.geonameid:
            rec = GeoAdmin2Code.query.get(item.geonameid)
            if rec is None:
                rec = GeoAdmin2Code(geonameid=int(item.geonameid))
                db.session.add(rec)
            rec.title = item.title
            rec.ascii_title = item.ascii_title
            rec.country_id, rec.admin1_code, rec.admin2_code = item.code.split('.')

    db.session.commit()


@geo.command('download')
def download() -> None:
    """Download geoname data."""
    os.makedirs('geoname_data', exist_ok=True)
    for filename in (
        'countryInfo.txt',
        'admin1CodesASCII.txt',
        'admin2Codes.txt',
        'IN.zip',
        'allCountries.zip',
        'alternateNames.zip',
    ):
        downloadfile(
            'http://download.geonames.org/export/dump/', filename, 'geoname_data'
        )


@geo.command('process')
def process() -> None:
    """Process downloaded geonames data."""
    load_country_info('geoname_data/countryInfo.txt')
    load_admin1_codes('geoname_data/admin1CodesASCII.txt')
    load_admin2_codes('geoname_data/admin2Codes.txt')
    load_geonames('geoname_data/IN.txt')
    load_geonames('geoname_data/allCountries.txt')
    load_alt_names('geoname_data/alternateNames.txt')


app.cli.add_command(geo)
