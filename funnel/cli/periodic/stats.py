"""Periodic statistics."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Sequence, Union, cast, overload
from typing_extensions import Literal
from urllib.parse import unquote

import click
import httpx
import pytz
import telegram
from asgiref.sync import async_to_sync
from dataclasses_json import DataClassJsonMixin
from dateutil.relativedelta import relativedelta
from furl import furl

from coaster.utils import midnight_to_utc, utcnow

from ... import app, models
from ...models import Mapped, Query, db, sa
from . import periodic

# --- Data structures ------------------------------------------------------------------


def trend_symbol(current: int, previous: int) -> str:
    """Return a trend symbol based on difference between current and previous."""
    if current > previous * 1.5:
        return '⏫'
    if current > previous:
        return '🔼'
    if current == previous:
        return '⏸️'
    if current * 1.5 < previous:
        return '⏬'
    return '🔽'


@dataclass
class DataSource:
    """Source for data (query object and datetime column)."""

    basequery: Query
    datecolumn: Mapped[datetime]


@dataclass
class ResourceStats:
    """Periodic counts for a resource."""

    day: int
    week: int
    month: int
    # The previous period counts are optional
    day_before: int = 0
    weekday_before: int = 0
    week_before: int = 0
    month_before: int = 0
    # Trend symbols are also optional
    day_trend: str = ''
    weekday_trend: str = ''
    week_trend: str = ''
    month_trend: str = ''

    def set_trend_symbols(self) -> None:
        self.day_trend = trend_symbol(self.day, self.day_before)
        self.weekday_trend = trend_symbol(self.day, self.weekday_before)
        self.week_trend = trend_symbol(self.week, self.week_before)
        self.month_trend = trend_symbol(self.month, self.month_before)


@dataclass
class MatomoResponse(DataClassJsonMixin):
    """Data in Matomo's API response."""

    label: str = ''
    nb_visits: int = 0
    nb_uniq_visitors: int = 0
    nb_users: int = 0
    url: Optional[str] = None
    segment: str = ''

    def get_url(self) -> Optional[str]:
        url = self.url
        if url:
            # If URL is a path (/path) or schemeless (//host/path), return as is
            if url.startswith('/'):
                return url
            # If there's no leading `/` and no `://`, prefix `https://`
            if '://' not in url:
                return f'https://{url}'
            # If neither, assume fully formed URL and return as is
            return url
        # If there's no URL in the data, look for a URL in the segment identifier
        if self.segment.startswith('pageUrl='):
            # Known prefixes: `pageUrl==` and `pageUrl=^` (9 chars)
            # The rest of the string is double escaped, so unquote twice
            return unquote(unquote(self.segment[9:]))
        return None


@dataclass
class MatomoData:
    """Matomo API data."""

    referrers: Sequence[MatomoResponse]
    socials: Sequence[MatomoResponse]
    pages: Sequence[MatomoResponse]
    visits_day: Optional[MatomoResponse] = None
    visits_week: Optional[MatomoResponse] = None
    visits_month: Optional[MatomoResponse] = None


# --- Matomo analytics -----------------------------------------------------------------


@overload
async def matomo_response_json(
    client: httpx.AsyncClient, url: str, sequence: Literal[True] = True
) -> Sequence[MatomoResponse]:
    ...


@overload
async def matomo_response_json(
    client: httpx.AsyncClient, url: str, sequence: Literal[False]
) -> Optional[MatomoResponse]:
    ...


async def matomo_response_json(
    client: httpx.AsyncClient, url: str, sequence: bool = True
) -> Union[Optional[MatomoResponse], Sequence[MatomoResponse]]:
    try:
        response = await client.get(url, timeout=30)
        response.raise_for_status()
        result = response.json()
        if sequence:
            if isinstance(result, list):
                return [MatomoResponse.from_dict(r) for r in result]
            return []  # Expected a list but didn't get one; treat as invalid response
        return MatomoResponse.from_dict(result)
    except httpx.HTTPError:
        return [] if sequence else None


async def matomo_stats(date: str = 'yesterday') -> MatomoData:
    # Dates in report timezone (for display)
    tz = pytz.timezone(app.config['TIMEZONE'])
    now = utcnow().astimezone(tz)
    today = midnight_to_utc(now)
    yesterday = today - relativedelta(days=1)
    last_week = yesterday - relativedelta(weeks=1)
    last_month = yesterday - relativedelta(months=1)
    week_range = f'{last_week.strftime("%Y-%m-%d")},{today.strftime("%Y-%m-%d")}'
    month_range = f'{last_month.strftime("%Y-%m-%d")},{today.strftime("%Y-%m-%d")}'
    if (
        not app.config.get('MATOMO_URL')
        or not app.config.get('MATOMO_ID')
        or not app.config.get('MATOMO_TOKEN')
    ):
        # No Matomo config
        return MatomoData(referrers=[], socials=[], pages=[])
    matomo_url = furl(app.config['MATOMO_URL'])
    matomo_url.add(
        {
            'token_auth': app.config['MATOMO_TOKEN'],
            'module': 'API',
            'idSite': app.config['MATOMO_ID'],
            'filter_limit': 10,  # Get top 10
            'format': 'json',
        }
    )
    referrers_url = matomo_url.copy().add(
        {
            'method': 'Referrers.getWebsites',
            'period': 'day',
            'date': date,
        }
    )
    socials_url = matomo_url.copy().add(
        {
            'method': 'Referrers.getSocials',
            'period': 'day',
            'date': date,
        }
    )
    pages_url = matomo_url.copy().add(
        {
            'method': 'Actions.getPageUrls',
            'period': 'day',
            'date': date,
        }
    )
    visits_day_url = matomo_url.copy().add(
        {
            'method': 'VisitsSummary.get',
            'period': 'day',
            'date': date,
        }
    )
    visits_week_url = matomo_url.copy().add(
        {
            'method': 'VisitsSummary.get',
            'period': 'range',
            'date': week_range,
        }
    )
    visits_month_url = matomo_url.copy().add(
        {
            'method': 'VisitsSummary.get',
            'period': 'range',
            'date': month_range,
        }
    )

    async with httpx.AsyncClient(follow_redirects=True) as client:
        (
            referrers,
            socials,
            pages,
            visits_day,
            visits_week,
            visits_month,
        ) = await asyncio.gather(
            matomo_response_json(client, str(referrers_url)),
            matomo_response_json(client, str(socials_url)),
            matomo_response_json(client, str(pages_url)),
            matomo_response_json(client, str(visits_day_url), sequence=False),
            matomo_response_json(client, str(visits_week_url), sequence=False),
            matomo_response_json(client, str(visits_month_url), sequence=False),
        )
    return MatomoData(
        referrers=referrers,
        socials=socials,
        pages=pages,
        visits_day=visits_day,
        visits_week=visits_week,
        visits_month=visits_month,
    )


# --- Internal database analytics ------------------------------------------------------


def data_sources() -> Dict[str, DataSource]:
    """Return sources for daily stats report."""
    return {
        # `user_sessions`, `app_user_sessions` and `returning_users` (added below) are
        # lookup keys, while the others are titles
        'user_sessions': DataSource(
            models.UserSession.query.distinct(models.UserSession.user_id),
            models.UserSession.accessed_at,
        ),
        'app_user_sessions': DataSource(
            db.session.query(sa.func.distinct(models.UserSession.user_id))
            .select_from(models.auth_client_user_session, models.UserSession)
            .filter(
                models.auth_client_user_session.c.user_session_id
                == models.UserSession.id
            ),
            cast(Mapped[datetime], models.auth_client_user_session.c.accessed_at),
        ),
        "New users": DataSource(
            models.User.query.filter(models.User.state.ACTIVE),
            models.User.created_at,
        ),
        "RSVPs": DataSource(
            models.Rsvp.query.filter(models.Rsvp.state.YES), models.Rsvp.created_at
        ),
        "Saved projects": DataSource(
            models.SavedProject.query, models.SavedProject.saved_at
        ),
        "Saved sessions": DataSource(
            models.SavedSession.query, models.SavedSession.saved_at
        ),
    }


async def user_stats() -> Dict[str, ResourceStats]:
    """Retrieve user statistics from internal database."""
    # Dates in report timezone (for display)
    tz = pytz.timezone(app.config['TIMEZONE'])
    now = utcnow().astimezone(tz)
    # Dates cast into UTC (for db queries)
    today = midnight_to_utc(now)
    yesterday = today - relativedelta(days=1)
    two_days_ago = today - relativedelta(days=2)
    last_week = today - relativedelta(weeks=1)
    last_week_and_a_day = today - relativedelta(days=8)
    two_weeks_ago = today - relativedelta(weeks=2)
    last_month = today - relativedelta(months=1)
    two_months_ago = today - relativedelta(months=2)

    stats: Dict[str, ResourceStats] = {
        key: ResourceStats(
            day=ds.basequery.filter(
                ds.datecolumn >= yesterday, ds.datecolumn < today
            ).count(),
            day_before=ds.basequery.filter(
                ds.datecolumn >= two_days_ago, ds.datecolumn < yesterday
            ).count(),
            weekday_before=ds.basequery.filter(
                ds.datecolumn >= last_week_and_a_day, ds.datecolumn < last_week
            ).count(),
            week=ds.basequery.filter(
                ds.datecolumn >= last_week, ds.datecolumn < today
            ).count(),
            week_before=ds.basequery.filter(
                ds.datecolumn >= two_weeks_ago, ds.datecolumn < last_week
            ).count(),
            month=ds.basequery.filter(
                ds.datecolumn >= last_month, ds.datecolumn < today
            ).count(),
            month_before=ds.basequery.filter(
                ds.datecolumn >= two_months_ago, ds.datecolumn < last_month
            ).count(),
        )
        for key, ds in data_sources().items()
    }

    stats.update(
        {
            'returning_users': ResourceStats(
                # User from day before was active yesterday
                day=models.UserSession.query.join(models.User)
                .filter(
                    models.UserSession.accessed_at >= yesterday,
                    models.UserSession.accessed_at < today,
                    models.User.created_at >= two_days_ago,
                    models.User.created_at < yesterday,
                )
                .distinct(models.UserSession.user_id)
                .count(),
                # User from last week was active this week
                week=models.UserSession.query.join(models.User)
                .filter(
                    models.UserSession.accessed_at >= last_week,
                    models.UserSession.accessed_at < today,
                    models.User.created_at >= two_weeks_ago,
                    models.User.created_at < last_week,
                )
                .distinct(models.UserSession.user_id)
                .count(),
                # User from last month was active this month
                month=models.UserSession.query.join(models.User)
                .filter(
                    models.UserSession.accessed_at >= last_month,
                    models.UserSession.accessed_at < today,
                    models.User.created_at >= two_months_ago,
                    models.User.created_at < last_month,
                )
                .distinct(models.UserSession.user_id)
                .count(),
            )
        }
    )

    for key in stats:
        if key not in ('user_sessions', 'app_user_sessions', 'returning_users'):
            stats[key].set_trend_symbols()

    return stats


# --- Commands -------------------------------------------------------------------------


@periodic.command('dailystats')
@async_to_sync
async def dailystats() -> None:
    """Publish daily stats to Telegram."""
    if (
        not app.config.get('TELEGRAM_STATS_APIKEY')
        or not app.config.get('TELEGRAM_STATS_CHATID')
        or not app.config.get('TIMEZONE')
    ):
        raise click.UsageError(
            "Configure TELEGRAM_STATS_APIKEY, TELEGRAM_STATS_CHATID and TIMEZONE in"
            " settings",
        )

    tz = pytz.timezone(app.config['TIMEZONE'])
    now = utcnow().astimezone(tz)
    display_date = now - relativedelta(days=1)

    user_data, matomo_data = await asyncio.gather(user_stats(), matomo_stats())
    message = (
        f"*Traffic #statistics for {display_date.strftime('%a, %-d %b %Y')}*\n"
        f"\n"
        f"*Active users*, of which\n"
        f"→ logged in, and\n"
        f"↝ also using other apps, and\n"
        f"⟳ returning new registered users from last period\n\n"
        f"*{display_date.strftime('%A')}:*"
    )
    if matomo_data.visits_day:
        message += f' {matomo_data.visits_day.nb_uniq_visitors}'
    message += (
        f" → {user_data['user_sessions'].day}"
        f" ↝ {user_data['app_user_sessions'].day}"
        f" ⟳ {user_data['returning_users'].day}\n"
        f"*Week:*"
    )
    if matomo_data.visits_week:
        message += f' {matomo_data.visits_week.nb_uniq_visitors}'
    message += (
        f" → {user_data['user_sessions'].week}"
        f" ↝ {user_data['app_user_sessions'].week}"
        f" ⟳ {user_data['returning_users'].week}\n"
        f"*Month:*"
    )
    if matomo_data.visits_month:
        message += f' {matomo_data.visits_month.nb_uniq_visitors}'
    message += (
        f" → {user_data['user_sessions'].month}"
        f" ↝ {user_data['app_user_sessions'].month}"
        f" ⟳ {user_data['returning_users'].month}\n"
        f"\n"
    )
    for key, data in user_data.items():
        if key not in ('user_sessions', 'app_user_sessions', 'returning_users'):
            message += (
                f"*{key}:*\n"
                f"{data.day_trend}{data.weekday_trend} {data.day} day,"
                f" {data.week_trend} {data.week} week,"
                f" {data.month_trend} {data.month} month\n"
                f"\n"
            )

    if matomo_data.pages:
        message += "\n*Top pages:* _(by visits)_\n"
        for mdata in matomo_data.pages:
            url = mdata.get_url()
            if url:
                message += f"{mdata.nb_visits}: [{mdata.label.strip()}]({url})\n"
            else:
                message += f"{mdata.nb_visits}: {mdata.label.strip()}\n"

    if matomo_data.referrers:
        message += "\n*Referrers:*\n"
        for mdata in matomo_data.referrers:
            message += f"{mdata.nb_visits}: {mdata.label.strip()}\n"

    if matomo_data.socials:
        message += "\n*Socials:*\n"
        for mdata in matomo_data.socials:
            message += f"{mdata.nb_visits}: {mdata.label.strip()}\n"

    bot = telegram.Bot(app.config["TELEGRAM_STATS_APIKEY"])
    await bot.send_message(
        text=message,
        parse_mode='markdown',
        chat_id=app.config['TELEGRAM_STATS_CHATID'],
        disable_notification=True,
        disable_web_page_preview=True,
        message_thread_id=app.config.get('TELEGRAM_STATS_THREADID'),
    )
