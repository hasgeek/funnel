# -*- coding: utf-8 -*-

from collections import defaultdict
from flask import render_template, json, jsonify, request, Response
from coaster.views import load_model, requestargs, jsonp
from baseframe import _
from .helpers import localize_micro_timestamp, localize_date
from .. import app, lastuser
from ..models import db, ProposalSpace, Session
from time import mktime
from .venue import venue_data, room_data
from pytz import timezone, utc
from datetime import datetime
from icalendar import Calendar, Event
from sqlalchemy import func


def session_data(sessions, timezone=None, with_modal_url=False):
    return [dict({
            "id": session.url_id,
            "title": session.title,
            "start": session.start.isoformat()+'Z',
            "end": session.end.isoformat()+'Z',
            "scoped_name": session.venue_room.scoped_name if session.venue_room else None,
            "is_break": session.is_break,
        }.items() + {
            "modal_url": session.url_for(with_modal_url)
        }.items() if with_modal_url else {}.items()) for session in sessions]


def date_js(d):
    if not d:
        return None
    return mktime(d.timetuple()) * 1000


def schedule_data(space):
    data = defaultdict(lambda: defaultdict(list))
    for session in space.sessions:
        day = str(localize_date(session.start, to_tz=space.timezone).date())
        slot = localize_date(session.start, to_tz=space.timezone).strftime('%H:%M')
        data[day][slot].append({
            "id": session.url_id,
            "title": session.title,
            "start": session.start.isoformat()+'Z',
            "end": session.end.isoformat()+'Z',
            "url": session.proposal.url_for(_external=True) if session.proposal else None,
            "json_url": session.proposal.url_for('json', _external=True) if session.proposal else None,
            "proposal": session.proposal.id if session.proposal else None,
            "room": session.venue_room.scoped_name if session.venue_room else None,
            "is_break": session.is_break,
            })
    schedule = []
    for day in sorted(data):
        daydata = {'date': day, 'slots': []}
        for slot in sorted(data[day]):
            daydata['slots'].append({
                'slot': slot,
                'sessions': data[day][slot]
                })
        schedule.append(daydata)
    return schedule


@app.route('/<space>/schedule')
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission=('view', 'siteadmin'), addlperms=lastuser.permissions)
def schedule_view(space):
    return render_template('schedule.html', space=space, venues=space.venues,
        from_date=date_js(space.date), to_date=date_js(space.date_upto),
        sessions=session_data(space.sessions, timezone=space.timezone, with_modal_url='view-popup'),
        timezone=timezone(space.timezone).utcoffset(datetime.now()).total_seconds(),
        rooms=dict([(room.scoped_name, {'title': room.title, 'bgcolor': room.bgcolor}) for room in space.rooms]),
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('schedule'), _("Schedule"))])


@app.route('/<space>/schedule/json')
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission=('view', 'siteadmin'), addlperms=lastuser.permissions)
def schedule_json(space):
    return jsonp(schedule=schedule_data(space),
        venues=[venue_data(venue) for venue in space.venues],
        rooms=[room_data(room) for room in space.rooms])

@app.route('/<space>/schedule/ical')
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission=('view', 'siteadmin'), addlperms=lastuser.permissions)
def schedule_ical(space):
    cal = Calendar()
    cal.add('prodid', "-//HasGeek Funnel for {event}//funnel.hasgeek.com//".format(event=space.title))
    cal.add('version', "2.0")
    cal.add('summary', "HasGeek Funnel for {event}".format(event=space.title))
    # Last updated time for calendar needs to be set. Cannot figure out how.
    # latest_session = Session.query.with_entities(func.max(Session.updated_at).label('updated_at')).filter_by(proposal_space=space).first()
    # cal.add('last-modified', latest_session[0])
    cal.add('x-wr-calname', "{event}".format(event=space.title))
    for session in space.sessions:
        event = Event()
        event.add('summary', session.title)
        event.add('uid', "/".join([space.name, session.url_name]) + '@' + request.host)
        event.add('dtstart', utc.localize(session.start).astimezone(timezone(space.timezone)))
        event.add('dtend', utc.localize(session.end).astimezone(timezone(space.timezone)))
        event.add('dtstamp', utc.localize(datetime.now()).astimezone(timezone(space.timezone)))
        event.add('created', utc.localize(session.created_at).astimezone(timezone(space.timezone)))
        event.add('last-modified', utc.localize(session.updated_at).astimezone(timezone(space.timezone)))
        if session.venue_room:
            location = [session.venue_room.title + " - " + session.venue_room.venue.title]
            if session.venue_room.venue.city:
                location.append(session.venue_room.venue.city)
            if session.venue_room.venue.country:
                location[len(location) - 1] += ", " + session.venue_room.venue.country
            else:
                location.append(session.venue_room.venue.country)
            event.add('location', "\n".join(location))
            if session.venue_room.venue.latitude and session.venue_room.venue.longitude:
                event.add('geo', (session.venue_room.venue.latitude, session.venue_room.venue.longitude))
        if session.description_text:
            event.add('description', session.description_text)
        if session.proposal:
            event.add('url', session.proposal.url_for(_external=True))
            if session.proposal.section:
                event.add('categories', [session.proposal.section.title])
        cal.add_component(event)
    return Response(cal.to_ical(), mimetype='text/calendar')


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
        'scheduled': session_data(space.sessions, timezone=space.timezone, with_modal_url='edit')
        }
    return render_template('schedule_edit.html', space=space, proposals=proposals,
        from_date=date_js(space.date), to_date=date_js(space.date_upto),
        timezone=timezone(space.timezone).utcoffset(datetime.now()).total_seconds(),
        rooms=dict([(room.scoped_name, {'title': room.title, 'vtitle': room.venue.title + " - " + room.title, 'bgcolor': room.bgcolor}) for room in space.rooms]),
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
        s = Session.query.filter_by(url_id=session['id']).first()
        s.start = session['start']
        s.end = session['end']
        db.session.commit()
    return jsonify(status=True)
