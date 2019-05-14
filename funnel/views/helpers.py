# -*- coding: utf-8 -*-

from flask import request
from coaster.gfm import markdown
from datetime import datetime
from flask_mail import Message
from funnel import app, funnelapp
from pytz import timezone as pytz_timezone, utc
from urlparse import urljoin
from .. import mail


def localize_micro_timestamp(timestamp, from_tz=utc, to_tz=utc):
    return localize_timestamp(int(timestamp) / 1000, from_tz, to_tz)


def localize_timestamp(timestamp, from_tz=utc, to_tz=utc):
    return localize_date(datetime.fromtimestamp(int(timestamp)), from_tz, to_tz)


def localize_date(date, from_tz=utc, to_tz=utc):
    if from_tz and to_tz:
        if isinstance(from_tz, basestring):
            from_tz = pytz_timezone(from_tz)
        if isinstance(to_tz, basestring):
            to_tz = pytz_timezone(to_tz)
        return from_tz.localize(date).astimezone(to_tz).replace(tzinfo=None)
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
        return u'{e}***'.format(e=email[:-3])
    username, domain = email.split('@')
    return u'{u}***@{d}'.format(u=username[:-3], d=domain)


def clear_old_session(response):
    if 'session' in request.cookies and app.config.get('SESSION_COOKIE_NAME') != 'session':
        response.set_cookie('session', '', expires=0, httponly=True)
    return response


app.after_request(clear_old_session)
