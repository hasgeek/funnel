from datetime import datetime

from pytz import utc
import pytest

from coaster.utils import utcnow
from funnel.views.sitemap import all_sitemap_days, all_sitemap_months, earliest_date


def test_dates_have_timezone():
    """Sitemap month and date functions require UTC timestamps"""
    aware_now = utcnow()
    naive_now = aware_now.replace(tzinfo=None)

    aware_months = all_sitemap_months(aware_now)
    aware_days = all_sitemap_days(aware_now)

    # When passed a UTC timestamp, both functions return results in UTC
    for source in (aware_months, aware_days):
        for dt in source:
            assert dt.tzinfo is utc

    # Both functions will not accept naive timestamps
    with pytest.raises(ValueError):
        all_sitemap_months(naive_now)

    with pytest.raises(ValueError):
        all_sitemap_days(naive_now)


def test_all_sitemap_months_days():
    """The sitemap months and days ranges are contiguous"""
    # Test dates 14, 15, 16 & 17, at midnight and noon, to see month/day rollover

    until = datetime(2020, 10, 14, tzinfo=utc)
    days = all_sitemap_days(until)
    months = all_sitemap_months(until)
    assert days[0] == datetime(2020, 10, 14, tzinfo=utc)
    assert days[-1] == datetime(2020, 9, 1, tzinfo=utc)
    assert months[0] == datetime(2020, 8, 1, tzinfo=utc)
    assert months[-1] == earliest_date

    until = datetime(2020, 10, 14, 12, 0, tzinfo=utc)
    days = all_sitemap_days(until)
    months = all_sitemap_months(until)
    assert days[0] == datetime(2020, 10, 14, tzinfo=utc)
    assert days[-1] == datetime(2020, 9, 1, tzinfo=utc)
    assert months[0] == datetime(2020, 8, 1, tzinfo=utc)
    assert months[-1] == earliest_date

    until = datetime(2020, 10, 15, tzinfo=utc)
    days = all_sitemap_days(until)
    months = all_sitemap_months(until)
    assert days[0] == datetime(2020, 10, 15, tzinfo=utc)
    assert days[-1] == datetime(2020, 9, 1, tzinfo=utc)
    assert months[0] == datetime(2020, 8, 1, tzinfo=utc)
    assert months[-1] == earliest_date

    until = datetime(2020, 10, 15, 12, 0, tzinfo=utc)
    days = all_sitemap_days(until)
    months = all_sitemap_months(until)
    assert days[0] == datetime(2020, 10, 15, tzinfo=utc)
    assert days[-1] == datetime(2020, 9, 1, tzinfo=utc)
    assert months[0] == datetime(2020, 8, 1, tzinfo=utc)
    assert months[-1] == earliest_date

    until = datetime(2020, 10, 16, tzinfo=utc)
    days = all_sitemap_days(until)
    months = all_sitemap_months(until)
    assert days[0] == datetime(2020, 10, 16, tzinfo=utc)
    assert days[-1] == datetime(2020, 10, 1, tzinfo=utc)
    assert months[0] == datetime(2020, 9, 1, tzinfo=utc)
    assert months[-1] == earliest_date

    until = datetime(2020, 10, 16, 12, 0, tzinfo=utc)
    days = all_sitemap_days(until)
    months = all_sitemap_months(until)
    assert days[0] == datetime(2020, 10, 16, tzinfo=utc)
    assert days[-1] == datetime(2020, 10, 1, tzinfo=utc)
    assert months[0] == datetime(2020, 9, 1, tzinfo=utc)
    assert months[-1] == earliest_date

    until = datetime(2020, 10, 17, tzinfo=utc)
    days = all_sitemap_days(until)
    months = all_sitemap_months(until)
    assert days[0] == datetime(2020, 10, 17, tzinfo=utc)
    assert days[-1] == datetime(2020, 10, 1, tzinfo=utc)
    assert months[0] == datetime(2020, 9, 1, tzinfo=utc)
    assert months[-1] == earliest_date

    until = datetime(2020, 10, 17, 12, 0, tzinfo=utc)
    days = all_sitemap_days(until)
    months = all_sitemap_months(until)
    assert days[0] == datetime(2020, 10, 17, tzinfo=utc)
    assert days[-1] == datetime(2020, 10, 1, tzinfo=utc)
    assert months[0] == datetime(2020, 9, 1, tzinfo=utc)
    assert months[-1] == earliest_date
