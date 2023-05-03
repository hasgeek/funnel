"""Sitemap views."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Tuple, Union

from flask import abort, render_template, url_for

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, MONTHLY, rrule
from pytz import utc

from baseframe import cache
from coaster.utils import utcnow
from coaster.views import ClassView, route

from .. import app, executor
from ..models import Account, Project, Proposal, Session, Update
from .decorators import xml_response
from .index import policy_pages

# --- Sitemap models -------------------------------------------------------------------


class ChangeFreq(str, Enum):
    """Enum for sitemap change frequency."""

    always = 'always'
    hourly = 'hourly'
    daily = 'daily'
    weekly = 'weekly'
    monthly = 'monthly'
    yearly = 'yearly'
    never = 'never'

    def __str__(self) -> str:
        """Render enum to string without using `.value` in templates."""
        return self.value


@dataclass
class SitemapIndex:
    """Sitemap index."""

    loc: str
    lastmod: Optional[datetime] = None


@dataclass
class SitemapPage:
    """Sitemap page."""

    loc: str
    lastmod: Optional[datetime] = None
    changefreq: Optional[ChangeFreq] = None
    priority: Optional[float] = None


# --- Helper functions -----------------------------------------------------------------


# The earliest date in Hasgeek's production database is 26 May 2011 (from Lastuser).
# We use 1 May here as we're only interested in the month. Hasjob's dataset starts
# earlier, from 14 Mar 2011, but this sitemap does not apply to Hasjob
earliest_date = utc.localize(datetime(2011, 5, 1))


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


def validate_daterange(
    year: Union[str, int], month: Union[str, int], day: Optional[Union[str, int]]
) -> Tuple[datetime, datetime]:
    """
    Validate year, month and day as provided to a view, and return a date range.

    Aborts with 404 if the values are not numeric, don't represent a valid date, or
    fall out of the bounds of earliest date to present day.

    If a day is provided, the resulting date range is for that day to the next, in UTC.
    If a day is not provided, the range is for the entire month.
    """
    try:
        year = int(year)
        month = int(month)
        if day is not None:
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
        dtstart = utc.localize(datetime(year, month, 1))
        dtend = dtstart + relativedelta(months=1)
    else:
        try:
            dtstart = utc.localize(datetime(year, month, day))
        except ValueError:
            # Invalid day
            abort(404)
        dtend = dtstart + timedelta(days=1)
    return dtstart, dtend


def changefreq_for_age(age: timedelta) -> ChangeFreq:
    """
    Provide a simple heuristic for the likelihood of a document being changed.

    If it changed within a given period, it may change again within the same period.
    Longer periods imply lesser chance of change.

    This simple mechanism is not content-aware and should not be considered a reliable
    indicator. It operates on the assumption that documents will be tweaked with
    repeated edits, first at a high rate, and then at a reducing rate as they mature.

    :param timedelta age: Age of the last change
    """
    if age < timedelta(days=1):  # Past day
        return ChangeFreq.hourly
    if age < timedelta(days=7):  # Past week
        return ChangeFreq.daily
    if age < timedelta(weeks=4):  # Past month
        return ChangeFreq.weekly
    if age < timedelta(weeks=12):  # Past three months
        return ChangeFreq.monthly
    # Longer? It's not likely to change much then
    return ChangeFreq.yearly


# --- Model queries --------------------------------------------------------------------


@executor.job
def query_account(dtstart: datetime, dtend: datetime, changefreq: ChangeFreq) -> list:
    return [
        SitemapPage(
            account.urls['view'],
            lastmod=account.updated_at.replace(second=0, microsecond=0),
            changefreq=changefreq,
        )
        for account in Account.all_public()
        .filter(Account.updated_at >= dtstart, Account.updated_at < dtend)
        .order_by(Account.updated_at.desc())
    ]


@executor.job
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
    @route('sitemap.xml')
    @xml_response
    @cache.cached(timeout=3600)
    def index(self) -> str:  # skipcq: PYL-R0201
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
    @xml_response
    @cache.cached(timeout=3600)
    def static(self) -> str:  # skipcq: PYL-R0201
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
    @xml_response
    @cache.cached(timeout=3600)
    def by_date(  # skipcq: PYL-R0201
        self, year: str, month: str, day: Optional[str]
    ) -> str:
        dtstart, dtend = validate_daterange(year, month, day)
        age = utcnow() - dtend
        changefreq = changefreq_for_age(age)

        jobs = [
            query_account.submit(dtstart, dtend, changefreq),
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
