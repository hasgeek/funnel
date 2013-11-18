# -*- coding: utf-8 -*-

from pytz import timezone as pytz_timezone, utc
from flask import render_template, json, Response, request, jsonify
from coaster.views import load_model, requestargs
from baseframe import _
from .. import app, lastuser
from ..models import db, ProposalSpace, Session
from datetime import datetime
from time import mktime


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


def date_js(d):
    if not d:
        return None
    return mktime(d.timetuple()) * 1000


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
    timezone = space.timezone
    if timezone:
        if isinstance(timezone, basestring):
            timezone = pytz_timezone(timezone)
    proposals = {
        'unscheduled': [{
                'title': proposal.title,
                'modal_url': proposal.url_for('schedule')
            } for proposal in space.proposals if proposal.confirmed and not proposal.session],
        'scheduled': [{
                'id': session.id,
                'title': session.title,
                'modal_url': session.url_for('edit'),
                'start': date_js(utc.localize(session.start).astimezone(timezone).replace(tzinfo=None) if timezone else session.start),
                'end': date_js(utc.localize(session.end).astimezone(timezone).replace(tzinfo=None) if timezone else session.end),
                'venue_room_id': session.venue_room_id,
                'is_break': session.is_break
            } for session in space.sessions]
        }
    return render_template('schedule_edit.html', space=space, proposals=proposals,
        from_date=date_js(space.date), to_date=date_js(space.date_upto),
        rooms=dict([(room.id, {'title': room.title, 'vtitle': room.venue.title + " - " + room.title, 'bgcolor': room.bgcolor}) for room in space.rooms]),
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('schedule'), _("Schedule")),
            (space.url_for('edit-schedule'), _("Edit"))])


@app.route('/<space>/schedule/update', methods=['POST'])
@lastuser.requires_login
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission=('siteadmin'), addlperms=lastuser.permissions)
@requestargs(('sessions', json.loads))
def schedule_update(space, sessions):
    timezone = space.timezone
    if timezone:
        if isinstance(timezone, basestring):
            timezone = pytz_timezone(timezone)
    for session in sessions:
        start = datetime.fromtimestamp(int(session['start'])/1000)
        end = datetime.fromtimestamp(int(session['end'])/1000)
        s = Session.query.filter_by(id=session['id']).first()
        s.start = timezone.localize(start).astimezone(utc).replace(tzinfo=None) if timezone else start
        s.end = timezone.localize(end).astimezone(utc).replace(tzinfo=None) if timezone else end
        db.session.commit()
    return jsonify(status=True)
