#! /usr/bin/env python
# -*- coding: utf-8 -*-

from collections import namedtuple
from datetime import date
import sys

from dateutil.relativedelta import relativedelta
import pytz
import requests

from coaster.manage import Manager, init_manager
from coaster.utils import midnight_to_utc
from funnel import app, funnelapp, lastuserapp, models

DataSource = namedtuple('DataSource', ['basequery', 'datecolumn'])
data_sources = {
    # `user_sessions` and `returning_users` (added below) are lookup keys,
    # while the others are titles
    'user_sessions': DataSource(
        models.UserSession.query.distinct(models.UserSession.user_id),
        models.UserSession.accessed_at,
    ),
    "New users": DataSource(
        models.User.query.filter(models.User.status == models.USER_STATUS.ACTIVE),
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


periodic = Manager(usage="Periodic tasks from cron (with recommended intervals)")


@periodic.command
def phoneclaims():
    """Sweep phone claims to close all unclaimed beyond expiry period (10m)"""
    models.UserPhoneClaim.delete_expired()
    models.db.session.commit()


@periodic.command
def growthstats():
    """
    Publish growth statistics to Telegram
    """
    if not app.config.get('TELEGRAM_STATS_BOT_TOKEN') or not app.config.get(
        'TELEGRAM_STATS_CHAT_ID'
    ):
        print(  # NOQA: T001
            "Configure TELEGRAM_STATS_BOT_TOKEN and TELEGRAM_STATS_CHAT_ID in settings",
            file=sys.stderr,
        )
        return
    tz = pytz.timezone('Asia/Kolkata')
    display_date = date.today() - relativedelta(days=1)
    today = midnight_to_utc(date.today(), tz)
    yesterday = today - relativedelta(days=1)
    two_days_ago = today - relativedelta(days=2)
    three_days_ago = today - relativedelta(days=3)
    last_week = today - relativedelta(weeks=1)
    two_weeks_ago = today - relativedelta(weeks=2)
    three_weeks_ago = today - relativedelta(weeks=3)
    last_month = today - relativedelta(months=1)
    two_months_ago = today - relativedelta(months=2)
    three_months_ago = today - relativedelta(months=3)

    stats = {
        key: {
            'day': ds.basequery.filter(
                ds.datecolumn >= yesterday, ds.datecolumn < today
            ).count(),
            'day_before': ds.basequery.filter(
                ds.datecolumn >= two_days_ago, ds.datecolumn < yesterday
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
        for key, ds in data_sources.items()
    }

    stats.update(
        {
            'returning_users': {
                # User from day before active yesterday
                'day': models.UserSession.query.join(models.User)
                .filter(
                    models.UserSession.accessed_at >= yesterday,
                    models.UserSession.accessed_at < today,
                    models.User.created_at >= two_days_ago,
                    models.User.created_at < yesterday,
                )
                .distinct(models.UserSession.user_id)
                .count(),
                'day_before': models.UserSession.query.join(models.User)
                .filter(
                    models.UserSession.accessed_at >= two_days_ago,
                    models.UserSession.accessed_at < yesterday,
                    models.User.created_at >= three_days_ago,
                    models.User.created_at < two_days_ago,
                )
                .distinct(models.UserSession.user_id)
                .count(),
                # User from last week active this week
                'week': models.UserSession.query.join(models.User)
                .filter(
                    models.UserSession.accessed_at >= last_week,
                    models.UserSession.accessed_at < today,
                    models.User.created_at >= two_weeks_ago,
                    models.User.created_at < last_week,
                )
                .distinct(models.UserSession.user_id)
                .count(),
                'week_before': models.UserSession.query.join(models.User)
                .filter(
                    models.UserSession.accessed_at >= two_weeks_ago,
                    models.UserSession.accessed_at < last_week,
                    models.User.created_at >= three_weeks_ago,
                    models.User.created_at < two_weeks_ago,
                )
                .distinct(models.UserSession.user_id)
                .count(),
                # User from last month active this week
                'month': models.UserSession.query.join(models.User)
                .filter(
                    models.UserSession.accessed_at >= last_month,
                    models.UserSession.accessed_at < today,
                    models.User.created_at >= two_months_ago,
                    models.User.created_at < last_month,
                )
                .distinct(models.UserSession.user_id)
                .count(),
                'month_before': models.UserSession.query.join(models.User)
                .filter(
                    models.UserSession.accessed_at >= two_months_ago,
                    models.UserSession.accessed_at < last_month,
                    models.User.created_at >= three_months_ago,
                    models.User.created_at < two_months_ago,
                )
                .distinct(models.UserSession.user_id)
                .count(),
            }
        }
    )

    def trend_symbol(current, previous):
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
        for period in ('day', 'week', 'month'):
            stats[key][period + '_trend'] = trend_symbol(
                stats[key][period], stats[key][period + '_before']
            )

    message = (
        f"*Growth statistics for {display_date}*\n"
        f"\n"
        f"*Active users,* of which ⟳ returning new users from last period:\n"
        f"{stats['user_sessions']['day_trend']} {stats['user_sessions']['day']} "
        f"{stats['returning_users']['day_trend']} ⟳{stats['returning_users']['day']} day\n"
        f"{stats['user_sessions']['week_trend']} {stats['user_sessions']['week']} "
        f"{stats['returning_users']['week_trend']} ⟳{stats['returning_users']['week']} week\n"
        f"{stats['user_sessions']['month_trend']} {stats['user_sessions']['month']} "
        f"{stats['returning_users']['month_trend']} ⟳{stats['returning_users']['month']} month\n"
        f"\n"
    )
    for key, data in stats.items():
        if key not in ('user_sessions', 'returning_users'):
            message += (
                f"*{key}:*\n"
                f"{data['day_trend']} {data['day']} day, "
                f"{data['week_trend']} {data['week']} week, "
                f"{data['month_trend']} {data['month']} month\n"
                f"\n"
            )

    requests.post(
        f'https://api.telegram.org/bot{app.config["TELEGRAM_STATS_BOT_TOKEN"]}/sendMessage',
        data={
            'chat_id': app.config['TELEGRAM_STATS_CHAT_ID'],
            'parse_mode': 'markdown',
            'text': message,
        },
    )


if __name__ == "__main__":
    manager = init_manager(
        app, models.db, models=models, funnelapp=funnelapp, lastuserapp=lastuserapp
    )
    manager.add_command('periodic', periodic)
    manager.run()
