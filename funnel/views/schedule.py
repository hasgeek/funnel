# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import datetime, timedelta
from icalendar import Calendar, Event, Alarm
from sqlalchemy import or_
from sqlalchemy.orm.exc import NoResultFound
from time import mktime

from flask import json, jsonify, request, Response, current_app

from coaster.utils import utcnow
from coaster.views import requestargs, jsonp, cors, route, render_with, requires_permission, UrlForView, ModelView

from .. import app, funnelapp, lastuser
from ..models import db, Session
from ..forms import (ProjectScheduleTransitionForm)
from .mixins import ProjectViewMixin, VenueRoomViewMixin
from .helpers import localize_date
from .venue import room_data
from .decorators import legacy_redirect


def session_data(session, with_modal_url=False, with_delete_url=False):
    return dict(
        {
            'id': session.url_id,
            'title': session.title,
            'start_at': session.start_at.isoformat() if session.scheduled else None,
            'end_at': session.end_at.isoformat() if session.scheduled else None,
            'speaker': session.speaker if session.speaker else None,
            'room_scoped_name': session.venue_room.scoped_name if session.venue_room else None,
            'is_break': session.is_break,
            'url_name_suuid': session.url_name_suuid,
            'url_name': session.url_name,
            'proposal_id': session.proposal_id,
            'speaker_bio': session.speaker_bio,
            'description': session.description,
            }.items()
        + dict({
            'modal_url': session.url_for(with_modal_url)
            } if with_modal_url else {}).items()
        + dict({
            'delete_url': session.url_for('delete')
            } if with_delete_url else {}).items()
        )


def session_list_data(sessions, with_modal_url=False, with_delete_url=False):
    return [session_data(session, with_modal_url, with_delete_url) for session in sessions]


def date_js(d):
    if not d:
        return None
    return mktime(d.timetuple()) * 1000


def schedule_data(project):
    data = defaultdict(lambda: defaultdict(list))
    for session in project.scheduled_sessions:
        day = str(localize_date(session.start_at, to_tz=project.timezone).date())
        slot = localize_date(session.start_at, to_tz=project.timezone).strftime('%H:%M')
        data[day][slot].append({
            'id': session.url_id,
            'title': session.title,
            'start_at': session.start_at.isoformat(),
            'end_at': session.end_at.isoformat(),
            'url': session.url_for(_external=True),
            'json_url': session.proposal.url_for('json', _external=True) if session.proposal else None,
            'proposal_url': session.proposal.url_for(_external=True) if session.proposal else None,
            'proposal': session.proposal.suuid if session.proposal else None,
            'feedback_url': session.url_for('feedback', _external=True) if session.proposal else None,
            'speaker': session.speaker,
            'room': session.venue_room.scoped_name if session.venue_room else None,
            'is_break': session.is_break,
            'description_text': session.description_text,
            'description': session.description,
            'speaker_bio': session.speaker_bio,
            'speaker_bio_text': session.speaker_bio_text,
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
    event.add('dtstart', session.start_at.astimezone(session.project.timezone))
    event.add('dtend', session.end_at.astimezone(session.project.timezone))
    event.add('dtstamp', utcnow().astimezone(session.project.timezone))
    event.add('created', session.created_at.astimezone(session.project.timezone))
    event.add('last-modified', session.updated_at.astimezone(session.project.timezone))
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
        if session.proposal.labels:
            event.add('categories', [l.title for l in session.proposal.labels])
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
class ProjectScheduleView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('')
    @render_with('schedule.html.jinja2')
    @requires_permission('view')
    def schedule(self):
        schedule_transition_form = ProjectScheduleTransitionForm(obj=self.obj)
        return dict(project=self.obj,
            from_date=date_js(self.obj.date), to_date=date_js(self.obj.date_upto),
            sessions=session_list_data(self.obj.scheduled_sessions, with_modal_url='view_popup'),
            timezone=self.obj.timezone.utcoffset(datetime.now()).total_seconds(),
            venues=[venue.current_access() for venue in self.obj.venues],
            rooms=dict([(room.scoped_name, {'title': room.title, 'bgcolor': room.bgcolor}) for room in self.obj.rooms]),
            schedule_transition_form=schedule_transition_form)

    @route('subscribe')
    @render_with('schedule_subscribe.html.jinja2')
    @requires_permission('view')
    def subscribe_schedule(self):
        return dict(project=self.obj, venues=self.obj.venues, rooms=self.obj.rooms)

    @route('json')
    @cors('*')
    @requires_permission('view')
    def schedule_json(self):
        return jsonp(schedule=schedule_data(self.obj),
            venues=[venue.current_access() for venue in self.obj.venues],
            rooms=[room_data(room) for room in self.obj.rooms])

    @route('ical')
    @requires_permission('view')
    def schedule_ical(self):
        cal = Calendar()
        cal.add('prodid', "-//Schedule for {event}//funnel.hasgeek.com//".format(event=self.obj.title))
        cal.add('version', "2.0")
        cal.add('summary', "Schedule for {event}".format(event=self.obj.title))
        # FIXME: Last updated time for calendar needs to be set. Cannot figure out how.
        # latest_session = Session.query.with_entities(func.max(Session.updated_at).label('updated_at')).filter_by(project=self.obj).first()
        # cal.add('last-modified', latest_session[0])
        cal.add('x-wr-calname', "{event}".format(event=self.obj.title))
        for session in self.obj.scheduled_sessions:
            cal.add_component(session_ical(session))
        return Response(cal.to_ical(), mimetype='text/calendar')

    @route('edit')
    @render_with('schedule_edit.html.jinja2')
    @lastuser.requires_login
    @requires_permission('edit-schedule')
    def edit_schedule(self):
        proposals = {
            'unscheduled': [{
                'title': proposal.title,
                'modal_url': proposal.url_for('schedule')
                } for proposal in self.obj.proposals_all if proposal.state.CONFIRMED and not proposal.state.SCHEDULED],
            'scheduled': session_list_data(self.obj.scheduled_sessions, with_modal_url='edit', with_delete_url=True)
            }
        # Set the proper range for the calendar to allow for date changes
        first_session = Session.query.filter(Session.scheduled, Session.project == self.obj).order_by(Session.start_at.asc()).first()
        last_session = Session.query.filter(Session.scheduled, Session.project == self.obj).order_by(Session.end_at.desc()).first()
        from_date = (first_session and first_session.start_at.date() < self.obj.date and first_session.start_at) or self.obj.date
        to_date = (last_session and last_session.start_at.date() > self.obj.date_upto and last_session.start_at) or self.obj.date_upto
        return dict(project=self.obj, proposals=proposals,
            from_date=date_js(from_date), to_date=date_js(to_date),
            timezone=self.obj.timezone.utcoffset(datetime.now()).total_seconds(),
            venues=[venue.current_access() for venue in self.obj.venues],
            rooms=dict([(room.scoped_name, {'title': room.title, 'vtitle': room.venue.title + " - " + room.title, 'bgcolor': room.bgcolor}) for room in self.obj.rooms]))

    @route('update', methods=['POST'])
    @render_with('schedule_edit.html.jinja2')
    @lastuser.requires_login
    @requires_permission('edit-schedule')
    @requestargs(('sessions', json.loads))
    def update_schedule(self, sessions):
        for session in sessions:
            try:
                s = Session.query.filter_by(project=self.obj, url_id=session['id']).one()
                s.start_at = session['start_at']
                s.end_at = session['end_at']
                db.session.commit()
            except NoResultFound:
                current_app.logger.error('{project} schedule update error: session = {session}'.format(project=self.obj.name, session=session))
        return jsonify(status=True)


@route('/<project>/schedule', subdomain='<profile>')
class FunnelProjectScheduleView(ProjectScheduleView):
    pass


ProjectScheduleView.init_app(app)
FunnelProjectScheduleView.init_app(funnelapp)


@route('/<profile>/<project>/schedule/<venue>/<room>')
class ScheduleVenueRoomView(VenueRoomViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('ical')
    @requires_permission('view')
    def schedule_room_ical(self):
        cal = Calendar()
        cal.add('prodid', "-//Schedule for room {room} at {venue} for {event}//funnel.hasgeek.com//".format(
            room=self.obj.title,
            venue=self.obj.venue.title,
            event=self.obj.venue.project.title,
            ))
        cal.add('version', "2.0")
        cal.add('summary', "Schedule for room {room} at {venue} for {event}".format(
            room=self.obj.title,
            venue=self.obj.venue.title,
            event=self.obj.venue.project.title,
            ))
        # Last updated time for calendar needs to be set. Cannot figure out how.
        # latest_session = Session.query.with_entities(func.max(Session.updated_at).label('updated_at')).filter_by(project=project).first()
        # cal.add('last-modified', latest_session[0])
        cal.add('x-wr-calname', "{event} - {room} @ {venue}".format(
            room=self.obj.title,
            venue=self.obj.venue.title,
            event=self.obj.venue.project.title,
            ))
        for session in self.obj.scheduled_sessions:
            cal.add_component(session_ical(session))
        return Response(cal.to_ical(), mimetype='text/calendar')

    @route('updates')
    @render_with('room_updates.html.jinja2')
    @requires_permission('view')
    def updates(self):
        now = utcnow()
        current = Session.query.filter(
            Session.start_at <= now, Session.end_at >= now,
            Session.project == self.obj.venue.project,
            or_(Session.venue_room == room, Session.is_break == True)  # NOQA
            ).first()
        next = Session.query.filter(
            Session.start_at > now,
            or_(Session.venue_room == room, Session.is_break == True),  # NOQA
            Session.project == self.obj.venue.project
            ).order_by(Session.start_at).first()
        if current:
            current.start_at = localize_date(current.start_at, to_tz=self.obj.venue.project.timezone)
            current.end_at = localize_date(current.end_at, to_tz=self.obj.venue.project.timezone)
        nextdiff = None
        if next:
            next.start_at = localize_date(next.start_at, to_tz=self.obj.venue.project.timezone)
            next.end_at = localize_date(next.end_at, to_tz=self.obj.venue.project.timezone)
            nextdiff = next.start_at.date() - now.date()
            nextdiff = nextdiff.total_seconds() / 86400
        return dict(room=self.obj, current=current, next=next, nextdiff=nextdiff)


@route('/<project>/schedule/<venue>/<room>', subdomain='<profile>')
class FunnelScheduleVenueRoomView(ScheduleVenueRoomView):
    pass


ScheduleVenueRoomView.init_app(app)
FunnelScheduleVenueRoomView.init_app(funnelapp)
