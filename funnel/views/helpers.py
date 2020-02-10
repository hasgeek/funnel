# -*- coding: utf-8 -*-

from datetime import datetime
from urllib.parse import urljoin

from flask import request
from flask_mail import Message

from pytz import timezone as pytz_timezone
from pytz import utc

from coaster.gfm import markdown

from .. import app, funnelapp, mail


def localize_micro_timestamp(timestamp, from_tz=utc, to_tz=utc):
    return localize_timestamp(int(timestamp) / 1000, from_tz, to_tz)


def localize_timestamp(timestamp, from_tz=utc, to_tz=utc):
    return localize_date(datetime.fromtimestamp(int(timestamp)), from_tz, to_tz)


def localize_date(date, from_tz=utc, to_tz=utc):
    if from_tz and to_tz:
        if isinstance(from_tz, str):
            from_tz = pytz_timezone(from_tz)
        if isinstance(to_tz, str):
            to_tz = pytz_timezone(to_tz)
        if date.tzinfo is None:
            date = from_tz.localize(date)
        return date.astimezone(to_tz)
    return date


@app.template_filter('url_join')
@funnelapp.template_filter('url_join')
def url_join(base, url=''):
    return urljoin(base, url)


def send_mail(sender, to, body, subject):
    msg = Message(sender=sender, subject=subject, recipients=[to])
    msg.body = body
    msg.html = markdown(msg.body)  # FIXME: This does not include HTML head/body tags
    mail.send(msg)


def mask_email(email):
    """
    Masks an email address

    >>> mask_email(u'foobar@example.com')
    u'foo***@example.com'
    >>> mask_email(u'not-email')
    u'not-em***'
    """
    if '@' not in email:
        return '{e}***'.format(e=email[:-3])
    username, domain = email.split('@')
    return '{u}***@{d}'.format(u=username[:-3], d=domain)


def clear_old_session(response):
    for cookie_name, domains in app.config.get('DELETE_COOKIES', {}).items():
        if cookie_name in request.cookies:
            for domain in domains:
                response.set_cookie(
                    cookie_name, '', expires=0, httponly=True, domain=domain
                )
    return response


app.after_request(clear_old_session)
