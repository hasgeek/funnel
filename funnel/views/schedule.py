# -*- coding: utf-8 -*-

from flask import render_template, json, Response, request, jsonify
from coaster.views import load_model, requestargs
from baseframe import _
from .helpers import localize_micro_timestamp, localize_date
from .. import app, lastuser
from ..models import db, ProposalSpace, Session
from datetime import datetime
from time import mktime


def session_data(sessions, timezone=None, with_modal_url=False):
    return [dict({
            "id": session.url_id,
            "title": session.title,
            "start": date_js(localize_date(session.start, to_tz=timezone)),
            "end": date_js(localize_date(session.end, to_tz=timezone)),
            "url": session.proposal.url_for() if session.proposal else None,
            "venue_room_id": session.venue_room_id,
            "is_break": session.is_break,
        }.items() + ({
            "modal_url": session.url_for('edit')
        }.items() if with_modal_url else {}.items())) for session in sessions]


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
    return Response(json.dumps(data), mimetype='application/json')


@app.route('/<space>/schedule/edit')
@lastuser.requires_login
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission=('edit', 'siteadmin'), addlperms=lastuser.permissions)
def schedule_edit(space):
    proposals = {
        'unscheduled': [{
                'title': proposal.title,
                'modal_url': proposal.url_for('schedule')
            } for proposal in space.proposals if proposal.confirmed and not proposal.session],
        'scheduled': session_data(space.sessions, timezone=space.timezone, with_modal_url=True)
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
    for session in sessions:
        start = datetime.fromtimestamp(int(session['start'])/1000)
        end = datetime.fromtimestamp(int(session['end'])/1000)
        s = Session.query.filter_by(id=session['id']).first()
        s.start = localize_micro_timestamp(session['start'], from_tz=space.timezone)
        s.end = localize_micro_timestamp(session['end'], from_tz=space.timezone)
        db.session.commit()
    return jsonify(status=True)
