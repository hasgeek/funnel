# -*- coding: utf-8 -*-

from collections import defaultdict
from pytz import timezone, utc
from datetime import datetime, timedelta
from icalendar import Calendar, Event, Alarm
from sqlalchemy import or_
from sqlalchemy.orm.exc import NoResultFound
from time import mktime

from flask import render_template, json, jsonify, request, Response, current_app

from coaster.views import load_models, requestargs, jsonp, cors, UrlForView, ModelView, route, render_with, requires_permission

from .. import app, funnelapp, lastuser
from ..models import db, Profile, Project, ProjectRedirect, Session, VenueRoom, Venue
from .helpers import localize_date
from .venue import venue_data, room_data


def session_data(sessions, with_modal_url=False, with_delete_url=False):
    return [
        dict(
            {
                'id': session.url_id,
                'title': session.title,
                'start': session.start.isoformat() + 'Z' if session.scheduled else None,
                'end': session.end.isoformat() + 'Z' if session.scheduled else None,
                'speaker': session.speaker if session.speaker else None,
                'room_scoped_name': session.venue_room.scoped_name if session.venue_room else None,
                'is_break': session.is_break,
                'url_name': session.url_name,
                'proposal_id': session.proposal_id,
            }.items() + dict({
                'modal_url': session.url_for(with_modal_url)
            } if with_modal_url else {}).items() + dict({
                'delete_url': session.url_for('delete')
            } if with_delete_url else {}).items()
        ) for session in sessions]


def date_js(d):
    if not d:
        return None
    return mktime(d.timetuple()) * 1000


def schedule_data(project):
    data = defaultdict(lambda: defaultdict(list))
    for session in project.scheduled_sessions:
        day = str(localize_date(session.start, to_tz=project.timezone).date())
        slot = localize_date(session.start, to_tz=project.timezone).strftime('%H:%M')
        data[day][slot].append({
            'id': session.url_id,
            'title': session.title,
            'start': session.start.isoformat() + 'Z',
            'end': session.end.isoformat() + 'Z',
            'url': session.url_for(_external=True),
            'json_url': session.proposal.url_for('json', _external=True) if session.proposal else None,
            'proposal_url': session.proposal.url_for(_external=True) if session.proposal else None,
            'proposal': session.proposal.id if session.proposal else None,
            'feedback_url': session.url_for('feedback', _external=True) if session.proposal else None,
            'speaker': session.speaker,
            'room': session.venue_room.scoped_name if session.venue_room else None,
            'is_break': session.is_break,
            'description_text': session.description_text,
            'description': session.description,
            'speaker_bio': session.speaker_bio,
            'speaker_bio_text': session.speaker_bio_text,
            'section_name': session.proposal.section.name if session.proposal and session.proposal.section else None,
            'section_title': session.proposal.section.title if session.proposal and session.proposal.section else None,
            'technical_level': session.proposal.technical_level if session.proposal and session.proposal.section else None,
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
    # This function is only called with scheduled sessions.
    # If for some reason it is used somewhere else and called with an unscheduled session,
    # this function should fail.
    if not session.scheduled:
        raise Exception(u"{0!r} is not scheduled".format(session))

    event = Event()
    event.add('summary', session.title)
    event.add('uid', "/".join([session.project.name, session.url_name]) + '@' + request.host)
    event.add('dtstart', utc.localize(session.start).astimezone(timezone(session.project.timezone)))
    event.add('dtend', utc.localize(session.end).astimezone(timezone(session.project.timezone)))
    event.add('dtstamp', utc.localize(datetime.now()).astimezone(timezone(session.project.timezone)))
    event.add('created', utc.localize(session.created_at).astimezone(timezone(session.project.timezone)))
    event.add('last-modified', utc.localize(session.updated_at).astimezone(timezone(session.project.timezone)))
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


@route('/<profile>/<project>/schedule')
class ProjectScheduleView(UrlForView, ModelView):
    model = Project
    route_model_map = {'profile': 'profile.name', 'project': 'name'}

    def loader(self, profile, project):
        return self.model.query.join(Profile).filter(
                Project.name == project, Profile.name == profile
            ).first_or_404()

    @route('')
    @render_with('schedule.html.jinja2')
    @requires_permission('view')
    def schedule_view(self):
        return dict(project=self.obj, venues=self.obj.venues,
            from_date=date_js(self.obj.date), to_date=date_js(self.obj.date_upto),
            sessions=session_data(self.obj.scheduled_sessions, with_modal_url='view-popup'),
            timezone=timezone(self.obj.timezone).utcoffset(datetime.now()).total_seconds(),
            rooms=dict([(room.scoped_name, {'title': room.title, 'bgcolor': room.bgcolor}) for room in self.obj.rooms]))

    @route('edit')
    @render_with('schedule_edit.html.jinja2')
    @lastuser.requires_login
    @requires_permission('edit-schedule')
    def schedule_edit(self):
        proposals = {
            'unscheduled': [{
                'title': proposal.title,
                'modal_url': proposal.url_for('schedule')
                } for proposal in self.obj.proposals_all if proposal.state.CONFIRMED and not proposal.session],
            'scheduled': session_data(self.obj.scheduled_sessions, with_modal_url='edit', with_delete_url=True)
            }
        # Set the proper range for the calendar to allow for date changes
        first_session = Session.query.filter(Session.scheduled, Session.project == self.obj).order_by(Session.start.asc()).first()
        last_session = Session.query.filter(Session.scheduled, Session.project == self.obj).order_by(Session.end.desc()).first()
        from_date = (first_session and first_session.start.date() < self.obj.date and first_session.start) or self.obj.date
        to_date = (last_session and last_session.start.date() > self.obj.date_upto and last_session.start) or self.obj.date_upto
        return dict(project=self.obj, proposals=proposals,
            from_date=date_js(from_date), to_date=date_js(to_date),
            timezone=timezone(self.obj.timezone).utcoffset(datetime.now()).total_seconds(),
            rooms=dict([(room.scoped_name, {'title': room.title, 'vtitle': room.venue.title + " - " + room.title, 'bgcolor': room.bgcolor}) for room in project.rooms]))


@route('/<project>/schedule', subdomain='<profile>')
class FunnelProjectScheduleView(ProjectScheduleView):
    pass


ProjectScheduleView.init_app(app)
FunnelProjectScheduleView.init_app(funnelapp)


@app.route('/<profile>/<project>/schedule/subscribe')
@funnelapp.route('/<project>/schedule/subscribe', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='view')
def schedule_subscribe(profile, project):
    return render_template('schedule_subscribe.html.jinja2',
        project=project, venues=project.venues, rooms=project.rooms)


@app.route('/<profile>/<project>/schedule/json')
@funnelapp.route('/<project>/schedule/json', subdomain='<profile>')
@cors('*')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='view')
def schedule_json(profile, project):
    return jsonp(schedule=schedule_data(project),
        venues=[venue_data(venue) for venue in project.venues],
        rooms=[room_data(room) for room in project.rooms])


@app.route('/<profile>/<project>/schedule/ical')
@funnelapp.route('/<project>/schedule/ical', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='view')
def schedule_ical(profile, project):
    cal = Calendar()
    cal.add('prodid', "-//Schedule for {event}//funnel.hasgeek.com//".format(event=project.title))
    cal.add('version', "2.0")
    cal.add('summary', "Schedule for {event}".format(event=project.title))
    # FIXME: Last updated time for calendar needs to be set. Cannot figure out how.
    # latest_session = Session.query.with_entities(func.max(Session.updated_at).label('updated_at')).filter_by(project=project).first()
    # cal.add('last-modified', latest_session[0])
    cal.add('x-wr-calname', "{event}".format(event=project.title))
    for session in project.scheduled_sessions:
        cal.add_component(session_ical(session))
    return Response(cal.to_ical(), mimetype='text/calendar')


@app.route('/<profile>/<project>/schedule/<venue>/<room>/ical')
@funnelapp.route('/<project>/schedule/<venue>/<room>/ical', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Venue, {'project': 'project', 'name': 'venue'}, 'venue'),
    (VenueRoom, {'venue': 'venue', 'name': 'room'}, 'room'),
    permission='view')
def schedule_room_ical(profile, project, venue, room):
    cal = Calendar()
    cal.add('prodid', "-//Schedule for room {room} at {venue} for {event}//funnel.hasgeek.com//".format(
        room=room.title,
        venue=venue.title,
        event=project.title,
        ))
    cal.add('version', "2.0")
    cal.add('summary', "Schedule for room {room} at {venue} for {event}".format(
        room=room.title,
        venue=venue.title,
        event=project.title,
        ))
    # Last updated time for calendar needs to be set. Cannot figure out how.
    # latest_session = Session.query.with_entities(func.max(Session.updated_at).label('updated_at')).filter_by(project=project).first()
    # cal.add('last-modified', latest_session[0])
    cal.add('x-wr-calname', "{event} - {room} @ {venue}".format(
        room=room.title,
        venue=venue.title,
        event=project.title,
        ))
    for session in room.scheduled_sessions:
        cal.add_component(session_ical(session))
    return Response(cal.to_ical(), mimetype='text/calendar')


@app.route('/<profile>/<project>/schedule/<venue>/<room>/updates')
@funnelapp.route('/<project>/schedule/<venue>/<room>/updates', subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Venue, {'project': 'project', 'name': 'venue'}, 'venue'),
    (VenueRoom, {'venue': 'venue', 'name': 'room'}, 'room'),
    permission='view')
def schedule_room_updates(profile, project, venue, room):
    now = datetime.utcnow()
    current = Session.query.filter(
        Session.start <= now, Session.end >= now,
        Session.project == project,
        or_(Session.venue_room == room, Session.is_break == True)  # NOQA
        ).first()
    next = Session.query.filter(
        Session.start > now,
        or_(Session.venue_room == room, Session.is_break == True),  # NOQA
        Session.project == project
        ).order_by(Session.start).first()
    if current:
        current.start = localize_date(current.start, to_tz=project.timezone)
        current.end = localize_date(current.end, to_tz=project.timezone)
    nextdiff = None
    if next:
        next.start = localize_date(next.start, to_tz=project.timezone)
        next.end = localize_date(next.end, to_tz=project.timezone)
        nextdiff = next.start.date() - now.date()
        nextdiff = nextdiff.total_seconds() / 86400
    print current, next
    return render_template('room_updates.html.jinja2', room=room, current=current, next=next, nextdiff=nextdiff)


@app.route('/<profile>/<project>/schedule/update', methods=['POST'])
@funnelapp.route('/<project>/schedule/update', methods=['POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='edit-schedule')
@requestargs(('sessions', json.loads))
def schedule_update(profile, project, sessions):
    for session in sessions:
        try:
            s = Session.query.filter_by(project=project, url_id=session['id']).one()
            s.start = session['start']
            s.end = session['end']
            db.session.commit()
        except NoResultFound:
            current_app.logger.error('{project} schedule update error: session = {session}'.format(project=project.name, session=session))
    return jsonify(status=True)
