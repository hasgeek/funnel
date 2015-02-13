# -*- coding: utf-8 -*-

from collections import defaultdict
from pytz import timezone, utc
from datetime import datetime, timedelta
from icalendar import Calendar, Event, Alarm
from sqlalchemy import or_
from time import mktime

from flask import render_template, json, jsonify, request, Response

from coaster.views import load_models, requestargs, jsonp

from .. import app, lastuser
from ..models import db, Profile, ProposalSpace, ProposalSpaceRedirect, Session, VenueRoom, Venue
from .helpers import localize_date
from .venue import venue_data, room_data


def session_data(sessions, timezone=None, with_modal_url=False, with_delete_url=False):
    return [dict({
            "id": session.url_id,
            "title": session.title,
            "start": session.start.isoformat() + 'Z',
            "end": session.end.isoformat() + 'Z',
            "room_scoped_name": session.venue_room.scoped_name if session.venue_room else None,
            "is_break": session.is_break,
            "url_name": session.url_name,
            "proposal_id": session.proposal_id,
        }.items() + dict({
            "modal_url": session.url_for(with_modal_url)
        } if with_modal_url else {}).items() + dict({
            "delete_url": session.url_for('delete')
        } if with_delete_url else {}).items()) for session in sessions]


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
            "start": session.start.isoformat() + 'Z',
            "end": session.end.isoformat() + 'Z',
            "url": session.url_for(_external=True),
            "json_url": session.proposal.url_for('json', _external=True) if session.proposal else None,
            "proposal": session.proposal.id if session.proposal else None,
            "feedback_url": session.url_for('feedback', _external=True) if session.proposal else None,
            "speaker": session.speaker,
            "room": session.venue_room.scoped_name if session.venue_room else None,
            "is_break": session.is_break,
            "description_text": session.description_text,
            "description": session.description,
            "speaker_bio": session.speaker_bio,
            "speaker_bio_text": session.speaker_bio_text,
            "section_name": session.proposal.section.name if session.proposal and session.proposal.section else None,
            "section_title": session.proposal.section.title if session.proposal and session.proposal.section else None,
            "technical_level": session.proposal.technical_level if session.proposal and session.proposal.section else None,
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


def session_ical(session):
    event = Event()
    event.add('summary', session.title)
    event.add('uid', "/".join([session.proposal_space.name, session.url_name]) + '@' + request.host)
    event.add('dtstart', utc.localize(session.start).astimezone(timezone(session.proposal_space.timezone)))
    event.add('dtend', utc.localize(session.end).astimezone(timezone(session.proposal_space.timezone)))
    event.add('dtstamp', utc.localize(datetime.now()).astimezone(timezone(session.proposal_space.timezone)))
    event.add('created', utc.localize(session.created_at).astimezone(timezone(session.proposal_space.timezone)))
    event.add('last-modified', utc.localize(session.updated_at).astimezone(timezone(session.proposal_space.timezone)))
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
        event.add('url', session.url_for(_external=True))
        if session.proposal.section:
            event.add('categories', [session.proposal.section.title])
    alarm = Alarm()
    alarm.add('trigger', timedelta(minutes=-5))
    alarm.add('action', 'display')
    desc = session.title
    if session.venue_room:
        desc += " in " + session.venue_room.title
    desc += " in 5 minutes"
    alarm.add('description', desc)
    event.add_component(alarm)
    return event


@app.route('/<space>/schedule', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
def schedule_view(profile, space):
    return render_template('schedule.html', space=space, venues=space.venues,
        from_date=date_js(space.date), to_date=date_js(space.date_upto),
        sessions=session_data(space.sessions, timezone=space.timezone, with_modal_url='view-popup'),
        timezone=timezone(space.timezone).utcoffset(datetime.now()).total_seconds(),
        rooms=dict([(room.scoped_name, {'title': room.title, 'bgcolor': room.bgcolor}) for room in space.rooms]))


@app.route('/<space>/schedule/subscribe', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
def schedule_subscribe(profile, space):
    return render_template('schedule_subscribe.html',
        space=space, venues=space.venues, rooms=space.rooms)


@app.route('/<space>/schedule/json', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
def schedule_json(profile, space):
    return jsonp(schedule=schedule_data(space),
        venues=[venue_data(venue) for venue in space.venues],
        rooms=[room_data(room) for room in space.rooms])


@app.route('/<space>/schedule/ical', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view')
def schedule_ical(profile, space):
    cal = Calendar()
    cal.add('prodid', "-//Schedule for {event}//funnel.hasgeek.com//".format(event=space.title))
    cal.add('version', "2.0")
    cal.add('summary', "Schedule for {event}".format(event=space.title))
    # Last updated time for calendar needs to be set. Cannot figure out how.
    # latest_session = Session.query.with_entities(func.max(Session.updated_at).label('updated_at')).filter_by(proposal_space=space).first()
    # cal.add('last-modified', latest_session[0])
    cal.add('x-wr-calname', "{event}".format(event=space.title))
    for session in space.sessions:
        cal.add_component(session_ical(session))
    return Response(cal.to_ical(), mimetype='text/calendar')


@app.route('/<space>/schedule/<venue>/<room>/ical', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Venue, {'proposal_space': 'space', 'name': 'venue'}, 'venue'),
    (VenueRoom, {'venue': 'venue', 'name': 'room'}, 'room'),
    permission='view')
def schedule_room_ical(profile, space, venue, room):
    cal = Calendar()
    cal.add('prodid', "-//Schedule for room {room} at {venue} for {event}//funnel.hasgeek.com//".format(
        room=room.title,
        venue=venue.title,
        event=space.title,
        ))
    cal.add('version', "2.0")
    cal.add('summary', "Schedule for room {room} at {venue} for {event}".format(
        room=room.title,
        venue=venue.title,
        event=space.title,
        ))
    # Last updated time for calendar needs to be set. Cannot figure out how.
    # latest_session = Session.query.with_entities(func.max(Session.updated_at).label('updated_at')).filter_by(proposal_space=space).first()
    # cal.add('last-modified', latest_session[0])
    cal.add('x-wr-calname', "{event} - {room} @ {venue}".format(
        room=room.title,
        venue=venue.title,
        event=space.title,
        ))
    for session in room.sessions:
        cal.add_component(session_ical(session))
    return Response(cal.to_ical(), mimetype='text/calendar')


@app.route('/<space>/schedule/<venue>/<room>/updates', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Venue, {'proposal_space': 'space', 'name': 'venue'}, 'venue'),
    (VenueRoom, {'venue': 'venue', 'name': 'room'}, 'room'),
    permission='view')
def schedule_room_updates(profile, space, venue, room):
    now = datetime.utcnow()
    current = Session.query.filter(
        Session.start <= now, Session.end >= now,
        Session.proposal_space == space,
        or_(Session.venue_room == room, Session.is_break == True)  # NOQA
        ).first()
    next = Session.query.filter(
        Session.start > now,
        or_(Session.venue_room == room, Session.is_break == True),  # NOQA
        Session.proposal_space == space
        ).order_by(Session.start).first()
    if current:
        current.start = localize_date(current.start, to_tz=space.timezone)
        current.end = localize_date(current.end, to_tz=space.timezone)
    nextdiff = None
    if next:
        next.start = localize_date(next.start, to_tz=space.timezone)
        next.end = localize_date(next.end, to_tz=space.timezone)
        nextdiff = next.start.date() - now.date()
        nextdiff = nextdiff.total_seconds() / 86400
    print current, next
    return render_template('room_updates.html', room=room, current=current, next=next, nextdiff=nextdiff)


@app.route('/<space>/schedule/edit', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='edit-schedule')
def schedule_edit(profile, space):
    proposals = {
        'unscheduled': [{
            'title': proposal.title,
            'modal_url': proposal.url_for('schedule')
            } for proposal in space.proposals_all if proposal.confirmed and not proposal.session],
        'scheduled': session_data(space.sessions, timezone=space.timezone, with_modal_url='edit', with_delete_url=True)
        }
    return render_template('schedule_edit.html', space=space, proposals=proposals,
        from_date=date_js(space.date), to_date=date_js(space.date_upto),
        timezone=timezone(space.timezone).utcoffset(datetime.now()).total_seconds(),
        rooms=dict([(room.scoped_name, {'title': room.title, 'vtitle': room.venue.title + " - " + room.title, 'bgcolor': room.bgcolor}) for room in space.rooms]))


@app.route('/<space>/schedule/update', methods=['POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='edit-schedule')
@requestargs(('sessions', json.loads))
def schedule_update(profile, space, sessions):
    for session in sessions:
        s = Session.query.filter_by(proposal_space=space, url_id=session['id']).one()
        s.start = session['start']
        s.end = session['end']
        db.session.commit()
    return jsonify(status=True)
