from __future__ import annotations

from collections import namedtuple
from datetime import timedelta
import sys

from flask.cli import AppGroup

from dateutil.relativedelta import relativedelta
import pytz
import requests

from coaster.utils import midnight_to_utc, utcnow

from .. import app, models
from ..models import db
from ..views.notification import dispatch_notification

# --- Data sources ---------------------------------------------------------------------

DataSource = namedtuple('DataSource', ['basequery', 'datecolumn'])


def data_sources():
    """Return sources for daily growth report."""
    return {
        # `user_sessions`, `app_user_sessions` and `returning_users` (added below) are
        # lookup keys, while the others are titles
        'user_sessions': DataSource(
            models.UserSession.query.distinct(models.UserSession.user_id),
            models.UserSession.accessed_at,
        ),
        'app_user_sessions': DataSource(
            db.session.query(db.func.distinct(models.UserSession.user_id))
            .select_from(models.auth_client_user_session, models.UserSession)
            .filter(
                models.auth_client_user_session.c.user_session_id
                == models.UserSession.id
            ),
            models.auth_client_user_session.c.accessed_at,
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


# --- Commands -------------------------------------------------------------------------


periodic = AppGroup(
    'periodic', help="Periodic tasks from cron (with recommended intervals)"
)


@periodic.command('phoneclaims')
def phoneclaims():
    """Sweep phone claims to close all unclaimed beyond expiry period (10m)."""
    models.UserPhoneClaim.delete_expired()
    db.session.commit()


@periodic.command('project_starting_alert')
def project_starting_alert():
    """Send notifications for projects that are about to start schedule (5m)."""
    # Rollback to the most recent 5 minute interval, to account for startup delay
    # for periodic job processes.
    use_now = db.session.query(
        db.func.date_trunc('hour', db.func.utcnow())
        + db.cast(db.func.date_part('minute', db.func.utcnow()), db.Integer)
        / 5
        * timedelta(minutes=5)
    ).scalar()

    # Find all projects that have a session starting between 10 and 15 minutes from
    # use_now, and where the same project did not have a session ending within
    # the prior hour.

    # Any eager-loading columns and relationships should be deferred with
    # db.defer(column) and db.noload(relationship). There are none as of this
    # commit.
    for project in (
        models.Project.starting_at(
            use_now + timedelta(minutes=10),
            timedelta(minutes=5),
            timedelta(minutes=60),
        )
        .options(db.load_only(models.Project.uuid))
        .all()
    ):
        dispatch_notification(
            models.ProjectStartingNotification(
                document=project,
                fragment=project.next_session_from(use_now + timedelta(minutes=10)),
            )
        )


@periodic.command('growthstats')
def growthstats():
    """Publish growth statistics to Telegram (midnight)."""
    if not app.config.get('TELEGRAM_STATS_BOT_TOKEN') or not app.config.get(
        'TELEGRAM_STATS_CHAT_ID'
    ):
        print(
            "Configure TELEGRAM_STATS_BOT_TOKEN and TELEGRAM_STATS_CHAT_ID in settings",
            file=sys.stderr,
        )
        return
    # Dates in report timezone (for display)
    tz = pytz.timezone('Asia/Kolkata')
    now = utcnow().astimezone(tz)
    display_date = now - relativedelta(days=1)
    # Dates cast into UTC (for db queries)
    today = midnight_to_utc(now)
    yesterday = today - relativedelta(days=1)
    two_days_ago = today - relativedelta(days=2)
    last_week = today - relativedelta(weeks=1)
    last_week_and_a_day = today - relativedelta(days=8)
    two_weeks_ago = today - relativedelta(weeks=2)
    last_month = today - relativedelta(months=1)
    two_months_ago = today - relativedelta(months=2)

    stats = {
        key: {
            'day': ds.basequery.filter(
                ds.datecolumn >= yesterday, ds.datecolumn < today
            ).count(),
            'day_before': ds.basequery.filter(
                ds.datecolumn >= two_days_ago, ds.datecolumn < yesterday
            ).count(),
            'weekday_before': ds.basequery.filter(
                ds.datecolumn >= last_week_and_a_day, ds.datecolumn < last_week
            ).count(),
            'week': ds.basequery.filter(
                ds.datecolumn >= last_week, ds.datecolumn < today
            ).count(),
            'week_before': ds.basequery.filter(
                ds.datecolumn >= two_weeks_ago, ds.datecolumn < last_week
            ).count(),
            'month': ds.basequery.filter(
                ds.datecolumn >= last_month, ds.datecolumn < today
            ).count(),
            'month_before': ds.basequery.filter(
                ds.datecolumn >= two_months_ago, ds.datecolumn < last_month
            ).count(),
        }
        for key, ds in data_sources().items()
    }

    stats.update(
        {
            'returning_users': {
                # User from day before was active yesterday
                'day': models.UserSession.query.join(models.User)
                .filter(
                    models.UserSession.accessed_at >= yesterday,
                    models.UserSession.accessed_at < today,
                    models.User.created_at >= two_days_ago,
                    models.User.created_at < yesterday,
                )
                .distinct(models.UserSession.user_id)
                .count(),
                # User from last week was active this week
                'week': models.UserSession.query.join(models.User)
                .filter(
                    models.UserSession.accessed_at >= last_week,
                    models.UserSession.accessed_at < today,
                    models.User.created_at >= two_weeks_ago,
                    models.User.created_at < last_week,
                )
                .distinct(models.UserSession.user_id)
                .count(),
                # User from last month was active this month
                'month': models.UserSession.query.join(models.User)
                .filter(
                    models.UserSession.accessed_at >= last_month,
                    models.UserSession.accessed_at < today,
                    models.User.created_at >= two_months_ago,
                    models.User.created_at < last_month,
                )
                .distinct(models.UserSession.user_id)
                .count(),
            }
        }
    )

    def trend_symbol(current, previous):
        """Return a trend symbol based on difference between current and previous."""
        if current > previous * 1.5:
            return '⏫'
        if current > previous:
            return '🔼'
        if current == previous:
            return '▶️'
        if current * 1.5 < previous:
            return '⏬'
        return '🔽'

    for key in stats:
        if key not in ('user_sessions', 'app_user_sessions', 'returning_users'):
            for period in ('day', 'week', 'month'):
                stats[key][period + '_trend'] = trend_symbol(
                    stats[key][period], stats[key][period + '_before']
                )
            stats[key]['weekday_trend'] = trend_symbol(
                stats[key]['day'], stats[key]['weekday_before']
            )

    message = (
        f"*Growth #statistics for {display_date.strftime('%a, %-d %b %Y')}*\n"
        f"\n"
        f"*Active users*, of which\n"
        f"↝ also using other apps, and\n"
        f"⟳ returning new users from last period\n\n"
        f"*{display_date.strftime('%A')}:* {stats['user_sessions']['day']}"
        f" ↝ {stats['app_user_sessions']['day']}"
        f" ⟳ {stats['returning_users']['day']}\n"
        f"*Week:* {stats['user_sessions']['week']}"
        f" ↝ {stats['app_user_sessions']['week']}"
        f" ⟳ {stats['returning_users']['week']}\n"
        f"*Month:* {stats['user_sessions']['month']}"
        f" ↝ {stats['app_user_sessions']['month']}"
        f" ⟳ {stats['returning_users']['month']}\n"
        f"\n"
    )
    for key, data in stats.items():
        if key not in ('user_sessions', 'app_user_sessions', 'returning_users'):
            message += (
                f"*{key}:*\n"
                f"{data['day_trend']}{data['weekday_trend']} {data['day']} day,"
                f" {data['week_trend']} {data['week']} week,"
                f" {data['month_trend']} {data['month']} month\n"
                f"\n"
            )

    requests.post(
        f'https://api.telegram.org/bot{app.config["TELEGRAM_STATS_BOT_TOKEN"]}'
        f'/sendMessage',
        data={
            'chat_id': app.config['TELEGRAM_STATS_CHAT_ID'],
            'parse_mode': 'markdown',
            'text': message,
        },
    )


app.cli.add_command(periodic)
