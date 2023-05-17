"""Test sitemap views."""

from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from pytz import utc
from werkzeug.exceptions import NotFound
import pytest

from coaster.utils import utcnow

from funnel.views import sitemap


def test_string_changefreq() -> None:
    """The ChangeFreq enum can be cast to and compared with str."""
    assert sitemap.ChangeFreq.daily == 'daily'
    assert str(sitemap.ChangeFreq.daily) == 'daily'


def test_dates_have_timezone() -> None:
    """Sitemap month and date functions require UTC timestamps."""
    aware_now = utcnow()
    naive_now = aware_now.replace(tzinfo=None)

    aware_months = sitemap.all_sitemap_months(aware_now)
    aware_days = sitemap.all_sitemap_days(aware_now)

    # When passed a UTC timestamp, both functions return results in UTC
    for source in (aware_months, aware_days):
        for dt in source:
            assert dt.tzinfo is utc

    # Both functions will not accept naive timestamps
    with pytest.raises(ValueError, match='must be specified in UTC'):
        sitemap.all_sitemap_months(naive_now)

    with pytest.raises(ValueError, match='UTC timezone required'):
        sitemap.all_sitemap_days(naive_now)


def test_all_sitemap_months_days() -> None:  # pylint: disable=too-many-statements
    """The sitemap months and days ranges are contiguous."""
    # Test dates 14, 15, 16 & 17, at midnight and noon, to see month/day rollover

    until = utc.localize(datetime(2020, 10, 14))
    days = sitemap.all_sitemap_days(until)
    months = sitemap.all_sitemap_months(until)
    assert days[0] == utc.localize(datetime(2020, 10, 14))
    assert days[-1] == utc.localize(datetime(2020, 9, 1))
    assert months[0] == utc.localize(datetime(2020, 8, 1))
    assert months[-1] == sitemap.earliest_date

    until = utc.localize(datetime(2020, 10, 14, 12, 0))
    days = sitemap.all_sitemap_days(until)
    months = sitemap.all_sitemap_months(until)
    assert days[0] == utc.localize(datetime(2020, 10, 14))
    assert days[-1] == utc.localize(datetime(2020, 9, 1))
    assert months[0] == utc.localize(datetime(2020, 8, 1))
    assert months[-1] == sitemap.earliest_date

    until = utc.localize(datetime(2020, 10, 15))
    days = sitemap.all_sitemap_days(until)
    months = sitemap.all_sitemap_months(until)
    assert days[0] == utc.localize(datetime(2020, 10, 15))
    assert days[-1] == utc.localize(datetime(2020, 9, 1))
    assert months[0] == utc.localize(datetime(2020, 8, 1))
    assert months[-1] == sitemap.earliest_date

    until = utc.localize(datetime(2020, 10, 15, 12, 0))
    days = sitemap.all_sitemap_days(until)
    months = sitemap.all_sitemap_months(until)
    assert days[0] == utc.localize(datetime(2020, 10, 15))
    assert days[-1] == utc.localize(datetime(2020, 9, 1))
    assert months[0] == utc.localize(datetime(2020, 8, 1))
    assert months[-1] == sitemap.earliest_date

    until = utc.localize(datetime(2020, 10, 16))
    days = sitemap.all_sitemap_days(until)
    months = sitemap.all_sitemap_months(until)
    assert days[0] == utc.localize(datetime(2020, 10, 16))
    assert days[-1] == utc.localize(datetime(2020, 10, 1))
    assert months[0] == utc.localize(datetime(2020, 9, 1))
    assert months[-1] == sitemap.earliest_date

    until = utc.localize(datetime(2020, 10, 16, 12, 0))
    days = sitemap.all_sitemap_days(until)
    months = sitemap.all_sitemap_months(until)
    assert days[0] == utc.localize(datetime(2020, 10, 16))
    assert days[-1] == utc.localize(datetime(2020, 10, 1))
    assert months[0] == utc.localize(datetime(2020, 9, 1))
    assert months[-1] == sitemap.earliest_date

    until = utc.localize(datetime(2020, 10, 17))
    days = sitemap.all_sitemap_days(until)
    months = sitemap.all_sitemap_months(until)
    assert days[0] == utc.localize(datetime(2020, 10, 17))
    assert days[-1] == utc.localize(datetime(2020, 10, 1))
    assert months[0] == utc.localize(datetime(2020, 9, 1))
    assert months[-1] == sitemap.earliest_date

    until = utc.localize(datetime(2020, 10, 17, 12, 0))
    days = sitemap.all_sitemap_days(until)
    months = sitemap.all_sitemap_months(until)
    assert days[0] == utc.localize(datetime(2020, 10, 17))
    assert days[-1] == utc.localize(datetime(2020, 10, 1))
    assert months[0] == utc.localize(datetime(2020, 9, 1))
    assert months[-1] == sitemap.earliest_date


def test_validate_daterange() -> None:
    """Test the values that validate_dayrange accepts."""
    # String dates are accepted
    assert sitemap.validate_daterange('2015', '11', '05') == (
        utc.localize(datetime(2015, 11, 5)),
        utc.localize(datetime(2015, 11, 6)),
    )

    # Integer dates are fine too
    assert sitemap.validate_daterange(2015, 11, 5) == (
        utc.localize(datetime(2015, 11, 5)),
        utc.localize(datetime(2015, 11, 6)),
    )

    # Zero padding is fine, as long as int(x) will accept it
    assert sitemap.validate_daterange('2015', '11', '00005') == (
        utc.localize(datetime(2015, 11, 5)),
        utc.localize(datetime(2015, 11, 6)),
    )

    # Day is optional, and date range is then for the full month
    assert sitemap.validate_daterange('2015', '11', None) == (
        utc.localize(datetime(2015, 11, 1)),
        utc.localize(datetime(2015, 12, 1)),
    )

    # Same with int year/month
    assert sitemap.validate_daterange(2015, 11, None) == (
        utc.localize(datetime(2015, 11, 1)),
        utc.localize(datetime(2015, 12, 1)),
    )

    # However, invalid dates and dates prior to earliest date or later than present day
    # are not accepted

    earlier_month = sitemap.earliest_date - relativedelta(months=1)
    earlier_day = sitemap.earliest_date - relativedelta(days=1)
    later_month = utcnow() + relativedelta(months=1)
    later_day = utcnow() + relativedelta(days=1)

    with pytest.raises(NotFound):
        sitemap.validate_daterange(earlier_month.year, earlier_month.month, None)

    with pytest.raises(NotFound):
        sitemap.validate_daterange(earlier_day.year, earlier_day.month, earlier_day.day)

    with pytest.raises(NotFound):
        sitemap.validate_daterange(later_month.year, later_month.month, None)

    with pytest.raises(NotFound):
        sitemap.validate_daterange(later_day.year, later_day.month, later_day.day)

    with pytest.raises(NotFound):
        sitemap.validate_daterange('2015', '00', '05')

    with pytest.raises(NotFound):
        sitemap.validate_daterange('2015', '00', None)

    with pytest.raises(NotFound):
        sitemap.validate_daterange('2015', '13', '05')

    with pytest.raises(NotFound):
        sitemap.validate_daterange('2015', '13', None)

    with pytest.raises(NotFound):
        sitemap.validate_daterange('2015', '11', '31')

    # Similarly, non-integer values are not accepted

    with pytest.raises(NotFound):
        sitemap.validate_daterange('invalid', '11', '05')

    with pytest.raises(NotFound):
        sitemap.validate_daterange('invalid', '11', None)

    with pytest.raises(NotFound):
        sitemap.validate_daterange('2015', 'invalid', '05')

    with pytest.raises(NotFound):
        sitemap.validate_daterange('2015', 'invalid', None)

    with pytest.raises(NotFound):
        sitemap.validate_daterange('2015', '11', 'invalid')


def test_changefreq_for_age() -> None:
    """Test that changefreq is age-appropriate."""
    # Less than a day
    assert sitemap.changefreq_for_age(timedelta(hours=1)) == sitemap.ChangeFreq.hourly
    assert sitemap.changefreq_for_age(timedelta(hours=10)) == sitemap.ChangeFreq.hourly
    # Less than a week
    assert sitemap.changefreq_for_age(timedelta(hours=40)) == sitemap.ChangeFreq.daily
    # Less than a month
    assert sitemap.changefreq_for_age(timedelta(days=15)) == sitemap.ChangeFreq.weekly
    # Less than a quarter
    assert sitemap.changefreq_for_age(timedelta(days=30)) == sitemap.ChangeFreq.monthly
    # More than a quarter
    assert sitemap.changefreq_for_age(timedelta(days=180)) == sitemap.ChangeFreq.yearly


@pytest.mark.dbcommit()
def test_sitemap(client) -> None:
    """Test sitemap endpoints (caveat: no content checks)."""
    expected_content_type = 'application/xml; charset=utf-8'

    rv = client.get('/sitemap.xml')
    assert rv.status_code == 200
    assert rv.content_type == expected_content_type
    assert b'/sitemap-static.xml' in rv.data

    rv = client.get('/sitemap-static.xml')
    assert rv.status_code == 200
    assert rv.content_type == expected_content_type

    rv = client.get('/sitemap-2015-11.xml')
    assert rv.status_code == 200
    assert rv.content_type == expected_content_type

    rv = client.get('/sitemap-2015-11-05.xml')
    assert rv.status_code == 200
    assert rv.content_type == expected_content_type

    rv = client.get('/sitemap-2010-12.xml')
    assert rv.status_code == 404
