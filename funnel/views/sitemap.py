from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, NamedTuple, Optional, Tuple, TypeVar, Union, cast

from flask import Response, abort, render_template, url_for

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, MONTHLY, rrule
from pytz import utc

from baseframe import cache
from coaster.utils import utcnow
from coaster.views import ClassView, route

from .. import app, executor
from ..models import Profile, Project, Proposal, Session, Update, db
from .index import policy_pages

# --- Sitemap models -------------------------------------------------------------------

# https://mypy.readthedocs.io/en/stable/generics.html#declaring-decorators
F = TypeVar('F', bound=Callable[..., Any])

# The earliest date in Hasgeek's production database is 26 May 2011 (from Lastuser).
# We use 1 May here as we're only interested in the month. Hasjob's dataset starts
# earlier, from 14 Mar 2011, but this sitemap does not apply to Hasjob
earliest_date = datetime(2011, 5, 1, tzinfo=utc)


class ChangeFreq(str, Enum):
    always = 'always'
    hourly = 'hourly'
    daily = 'daily'
    weekly = 'weekly'
    monthly = 'monthly'
    yearly = 'yearly'
    never = 'never'

    # This method supports rendering in templates without using `.value`
    def __str__(self) -> str:
        return self.value


class SitemapIndex(NamedTuple):
    loc: str
    lastmod: Optional[datetime] = None


class SitemapPage(NamedTuple):
    loc: str
    lastmod: Optional[datetime] = None
    changefreq: Optional[ChangeFreq] = None
    priority: Optional[float] = None


# --- Helper functions -----------------------------------------------------------------


def is_xml(f: F) -> F:
    """Wrap the view result in a :class:`Response` with XML mimetype."""

    @wraps(f)
    def wrapper(*args, **kwargs) -> Response:
        return Response(f(*args, **kwargs), mimetype='application/xml')

    return cast(F, wrapper)


def all_sitemap_days(until: datetime) -> list:
    """Return recent days, for links in the sitemap index."""
    if until.tzinfo != utc:
        raise ValueError("UTC timezone required")
    days = list(
        rrule(
            freq=DAILY,
            dtstart=(until - timedelta(days=15)).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            ),
            until=until,
        )
    )
    days.reverse()
    return days


def all_sitemap_months(until: datetime) -> list:
    """Return all months from the earliest date, minus the recent days."""
    months = list(
        rrule(
            freq=MONTHLY,
            dtstart=earliest_date,
            until=until
            - timedelta(days=15)
            - relativedelta(months=1, hour=0, minute=0, second=0, microsecond=0),
        )
    )
    months.reverse()
    return months


def cleanup_session(f: F) -> F:
    """
    Remove the database session after calling the wrapped function.

    A transaction error in a background job will affect future queries, so the
    transaction must be rolled back.

    Required until this underlying issue is resolved:
    https://github.com/dchevell/flask-executor/issues/15
    """

    @wraps(f)
    def wrapper(*args, **kwargs) -> Response:
        try:
            result = f(*args, **kwargs)
        finally:
            db.session.remove()
        return result

    return cast(F, wrapper)


# --- Model queries --------------------------------------------------------------------


@executor.job
@cleanup_session
def query_profile(dtstart: datetime, dtend: datetime, changefreq: ChangeFreq) -> list:
    return [
        SitemapPage(
            profile.urls['view'],
            lastmod=profile.updated_at.replace(second=0, microsecond=0),
            changefreq=changefreq,
        )
        for profile in Profile.all_public()
        .filter(Profile.updated_at >= dtstart, Profile.updated_at < dtend)
        .order_by(Profile.updated_at.desc())
    ]


@executor.job
@cleanup_session
def query_project(dtstart: datetime, dtend: datetime, changefreq: ChangeFreq) -> list:
    return [
        SitemapPage(
            project_url,
            lastmod=project.updated_at.replace(second=0, microsecond=0),
            changefreq=changefreq,
        )
        for project in Project.all_unsorted()
        .filter(Project.updated_at >= dtstart, Project.updated_at < dtend)
        .order_by(Project.updated_at.desc())
        for project_url in [
            project.urls['view'],
            project.urls['comments'],
            project.urls['session_videos'],
            project.urls['view_proposals'],
            project.urls['schedule'],
            project.urls['crew'],
        ]
    ]


@executor.job
@cleanup_session
def query_update(dtstart: datetime, dtend: datetime, changefreq: ChangeFreq) -> list:
    return [
        SitemapPage(
            update.urls['view'],
            lastmod=update.updated_at.replace(second=0, microsecond=0),
            changefreq=changefreq,
        )
        for update in Update.all_published_public()
        .filter(Update.published_at >= dtstart, Update.published_at < dtend)
        .order_by(Update.published_at.desc())
    ]


@executor.job
@cleanup_session
def query_proposal(dtstart: datetime, dtend: datetime, changefreq: ChangeFreq) -> list:
    return [
        SitemapPage(
            proposal.urls['view'],
            lastmod=proposal.updated_at.replace(second=0, microsecond=0),
            changefreq=changefreq,
        )
        for proposal in Proposal.all_public()
        .filter(Proposal.updated_at >= dtstart, Proposal.updated_at < dtend)
        .order_by(Proposal.updated_at.desc())
    ]


@executor.job
@cleanup_session
def query_session(dtstart: datetime, dtend: datetime, changefreq: ChangeFreq) -> list:
    return [
        SitemapPage(
            session.urls['view'],
            lastmod=session.updated_at.replace(second=0, microsecond=0),
            changefreq=changefreq,
        )
        for session in Session.all_public()
        .filter(Session.updated_at >= dtstart, Session.updated_at < dtend)
        .order_by(Session.updated_at.desc())
    ]


# --- Views ----------------------------------------------------------------------------


@route('/')
class SitemapView(ClassView):
    @staticmethod
    def validate_daterange(
        year: Union[str, int], month: Union[str, int], day: Optional[Union[str, int]]
    ) -> Tuple[datetime, datetime]:
        try:
            year = int(year)
            month = int(month)
            if day:
                day = int(day)
        except ValueError:
            abort(404)
        now = utcnow()
        if month < 1 or month > 12:
            abort(404)
        if (year, month) < (earliest_date.year, earliest_date.month):
            abort(404)
        if (year, month) > (now.year, now.month):
            abort(404)
        if day and (year, month, day) > (now.year, now.month, now.day):
            abort(404)

        # Now make a date range
        if not day:
            dtstart = datetime(year, month, 1, tzinfo=utc)
            dtend = dtstart + relativedelta(months=1)
        else:
            try:
                dtstart = datetime(year, month, day, tzinfo=utc)
            except ValueError:
                # Invalid day
                abort(404)
            dtend = dtstart + timedelta(days=1)
        return dtstart, dtend

    @route('sitemap.xml')
    @is_xml
    @cache.cached(timeout=3600)
    def index(self) -> str:
        now = utcnow()
        sitemaps = (
            [SitemapIndex(url_for('SitemapView_static', _external=True))]
            + [
                SitemapIndex(
                    url_for(
                        'SitemapView_by_date',
                        # strftime is required for zero padded numbers (month and day)
                        year=date.strftime('%Y'),
                        month=date.strftime('%m'),
                        day=date.strftime('%d'),
                        _external=True,
                    ),
                    lastmod=min(now, date + timedelta(days=1)),
                )
                for date in all_sitemap_days(now)
            ]
            + [
                SitemapIndex(
                    url_for(
                        'SitemapView_by_date',
                        year=date.strftime('%Y'),
                        month=date.strftime('%m'),
                        _external=True,
                    ),
                    lastmod=date + relativedelta(months=1),
                )
                for date in all_sitemap_months(now)
            ]
        )
        return render_template(
            'sitemapindex.xml.jinja2',
            sitemaps=sitemaps,
        )

    @route('sitemap-static.xml')
    @is_xml
    @cache.cached(timeout=3600)
    def static(self) -> str:
        pages = [
            SitemapPage(
                url_for('index', _external=True),
                changefreq=ChangeFreq.hourly,
                priority=1.0,
            ),
            SitemapPage(url_for('about', _external=True), priority=0.7),
            SitemapPage(url_for('contact', _external=True), priority=0.6),
            SitemapPage(url_for('policy', _external=True), priority=0.7),
        ] + [
            SitemapPage(url_for('policy', path=page.path, _external=True))
            for page in policy_pages
        ]
        return render_template('sitemap.xml.jinja2', sitemap=pages)

    # The following routes can't use `int:` prefix as that strips zero padding

    @route('sitemap-<year>-<month>.xml', defaults={'day': None})
    @route('sitemap-<year>-<month>-<day>.xml')
    @is_xml
    # @cache.cached(timeout=3600)
    def by_date(self, year: str, month: str, day: Optional[str]) -> str:
        dtstart, dtend = self.validate_daterange(year, month, day)
        age = utcnow() - dtend
        if age < timedelta(days=1):  # Past day
            changefreq = ChangeFreq.hourly
        elif age < timedelta(days=7):  # Past week
            changefreq = ChangeFreq.daily
        elif age < timedelta(weeks=4):  # Past month
            changefreq = ChangeFreq.weekly
        elif age < timedelta(weeks=12):  # Past three months
            changefreq = ChangeFreq.monthly
        else:
            changefreq = ChangeFreq.yearly

        jobs = [
            query_profile.submit(dtstart, dtend, changefreq),
            query_project.submit(dtstart, dtend, changefreq),
            query_update.submit(dtstart, dtend, changefreq),
            query_proposal.submit(dtstart, dtend, changefreq),
            query_session.submit(dtstart, dtend, changefreq),
        ]
        sitemap = [
            link
            for query_results in (job.result() for job in jobs)
            for link in query_results
        ]
        # Sort pages by lastmod, in descending order
        sitemap.sort(key=lambda page: page.lastmod, reverse=True)
        return render_template('sitemap.xml.jinja2', sitemap=sitemap)


SitemapView.init_app(app)
