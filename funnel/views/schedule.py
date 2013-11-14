# -*- coding: utf-8 -*-

from pytz import timezone as pytz_timezone, utc
from flask import render_template, json, Markup, Response
from coaster.views import load_model
from baseframe import _
from .. import app, lastuser
from ..models import ProposalSpace
from datetime import timedelta
import simplejson as json


def session_data(sessions, timezone=None):
    if timezone:
        if isinstance(timezone, basestring):
            timezone = pytz_timezone(timezone)
    data = [{
            "id": session.url_id,
            "title": session.title,
            "start": utc.localize(session.start).astimezone(timezone) if timezone else session.start,
            "end": utc.localize(session.end).astimezone(timezone) if timezone else session.end,
            "url": session.proposal.url_for() if session.proposal else None,
        } for session in sessions]
    return data

def inactive_days(date_from, date_to):
    inactive = range(0,7)
    diff = date_to - date_from
    while diff.total_seconds() >= 0:
        day = date_from.weekday() + 1
        if day == 7:
            day = 0
        inactive.remove(day)
        date_from = date_from + timedelta(days=1)
        diff = date_to - date_from
    first_day=date_from.weekday() + 1
    if first_day == 7:
        first_day = 0
    return dict(days=json.dumps(inactive), first_day=first_day)

@app.route('/<space>/schedule')
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission=('view', 'siteadmin'), addlperms=lastuser.permissions)
def schedule_view(space):
    return render_template('schedule.html', space=space, venues=space.venues,
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('schedule'), _("Schedule"))])


@app.route('/<space>/schedule/json')
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission=('view', 'siteadmin'), addlperms=lastuser.permissions)
def schedule_json(space):
    data = session_data(space.sessions, timezone=space.timezone)
    for item in data:
        item['start'] = item['start'].isoformat()
        item['end'] = item['end'].isoformat()
    return Response(json.dumps(data), mimetype='application/json')


@app.route('/<space>/schedule/edit')
@lastuser.requires_login
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission=('edit', 'siteadmin'), addlperms=lastuser.permissions)
def schedule_edit(space):
    return render_template('schedule_edit.html', space=space, venues=space.venues, inactive=inactive_days(space.date, space.date_upto),
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('schedule'), _("Schedule")),
            (space.url_for('edit-schedule'), _("Edit"))])
