# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import timedelta
from time import mktime

from sqlalchemy.orm.exc import NoResultFound

from flask import Response, current_app, json, jsonify, request

from icalendar import Alarm, Calendar, Event

from baseframe import localize_timezone
from coaster.utils import utcnow
from coaster.views import (
    ModelView,
    UrlForView,
    cors,
    jsonp,
    render_with,
    requestargs,
    requires_permission,
    requires_roles,
    route,
)

from .. import app, funnelapp
from ..forms import ProjectScheduleTransitionForm, SavedProjectForm
from ..models import Project, Proposal, Session, VenueRoom, db
from .decorators import legacy_redirect
from .helpers import localize_date, requires_login
from .mixins import ProjectViewMixin, VenueRoomViewMixin
from .venue import room_data


def session_data(session, with_modal_url=False, with_delete_url=False):
    data = {
        'id': session.url_id,
        'title': session.title,
        'start_at': (
            localize_timezone(session.start_at, tz=session.project.timezone)
            if session.scheduled
            else None
        ),
        'end_at': (
            localize_timezone(session.end_at, tz=session.project.timezone)
            if session.scheduled
            else None
        ),
        'timezone': session.project.timezone.zone,
        'speaker': session.speaker if session.speaker else None,
        'room_scoped_name': (
            session.venue_room.scoped_name if session.venue_room else None
        ),
        'is_break': session.is_break,
        'url_name_uuid_b58': session.url_name_uuid_b58,
        'url_name': session.url_name,
        'proposal_id': session.proposal_id,
        'description': session.description,
        'speaker_bio': session.speaker_bio,
        'url': session.url_for(_external=True),
        'json_url': (
            session.proposal.url_for('json', _external=True)
            if session.proposal
            else None
        ),
        'proposal_url': (
            session.proposal.url_for(_external=True) if session.proposal else None
        ),
        'proposal': session.proposal.uuid_b58 if session.proposal else None,
        'feedback_url': (
            session.url_for('feedback', _external=True) if session.proposal else None
        ),
        'room': (session.venue_room.scoped_name if session.venue_room else None),
    }
    if with_modal_url:
        data.update({'modal_url': session.url_for(with_modal_url)})
    if with_delete_url:
        data.update({'delete_url': session.url_for('delete')})
    return data


def session_list_data(sessions, with_modal_url=False, with_delete_url=False):
    return [
        session_data(session, with_modal_url, with_delete_url) for session in sessions
    ]


def date_js(d):
    if not d:
        return None
    return mktime(d.timetuple()) * 1000


def schedule_data(project, with_slots=True, scheduled_sessions=None):
    scheduled_sessions = scheduled_sessions or session_list_data(
        project.scheduled_sessions
    )
    data = defaultdict(lambda: defaultdict(list))
    start_end_datetime = defaultdict(dict)
    for session in scheduled_sessions:
        day = str(session['start_at'].date())
        # calculate the start and end time for the day
        if 'start_at' not in start_end_datetime[day]:
            start_end_datetime[day]['start_at'] = session['start_at']
        if (
            'end_at' not in start_end_datetime[day]
            or session['end_at'] > start_end_datetime[day]['end_at']
        ):
            start_end_datetime[day]['end_at'] = session['end_at']

        if with_slots:
            slot = session['start_at'].strftime('%H:%M')
            session['start_at'] = session['start_at'].isoformat()
            session['end_at'] = session['end_at'].isoformat()
            data[day][slot].append(session)
        else:
            data[day] = {}
    schedule = []
    for day in sorted(data):
        daydata = {'date': day, 'slots': []}
        daydata['start_at'] = start_end_datetime[day]['start_at'].isoformat()
        daydata['end_at'] = start_end_datetime[day]['end_at'].isoformat()
        for slot in sorted(data[day]):
            daydata['slots'].append({'slot': slot, 'sessions': data[day][slot]})
        schedule.append(daydata)
    return schedule


def session_ical(session):
    # This function is only called with scheduled sessions.
    # If for some reason it is used somewhere else and called with an unscheduled session,
    # this function should fail.
    if not session.scheduled:
        raise Exception("{0!r} is not scheduled".format(session))

    event = Event()
    event.add('summary', session.title)
    event.add('uid', f'session/{session.uuid_b58}@{request.host}')
    event.add('dtstart', session.start_at_localized)
    event.add('dtend', session.end_at_localized)
    event.add('dtstamp', utcnow())
    event.add('created', session.created_at)
    event.add('last-modified', session.updated_at)
    if session.venue_room:
        location = [session.venue_room.title + " - " + session.venue_room.venue.title]
        if session.venue_room.venue.city:
            location.append(session.venue_room.venue.city)
        if session.venue_room.venue.country:
            location[len(location) - 1] += ", " + session.venue_room.venue.country
        else:
            location.append(session.venue_room.venue.country)
        event.add('location', "\n".join(location))
        if session.venue_room.venue.has_coordinates:
            event.add('geo', session.venue_room.venue.coordinates)
    if session.description_text:
        event.add('description', session.description_text)
    if session.proposal:
        event.add('url', session.url_for(_external=True))
        if session.proposal.labels:
            event.add('categories', [l.title for l in session.proposal.labels])
    alarm = Alarm()
    alarm.add('trigger', timedelta(minutes=-5))
    alarm.add('action', 'display')
    # FIXME: Needs an i18n-friendly approach
    desc = session.title
    if session.venue_room:
        desc += " in " + session.venue_room.title
    desc += " in 5 minutes"
    alarm.add('description', desc)
    event.add_component(alarm)
    return event


@Project.views('schedule')
@route('/<profile>/<project>/schedule')
class ProjectScheduleView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('')
    @render_with('schedule.html.jinja2')
    @requires_roles({'reader'})
    def schedule(self):
        schedule_transition_form = ProjectScheduleTransitionForm(obj=self.obj)
        project_save_form = SavedProjectForm()
        scheduled_sessions_list = session_list_data(
            self.obj.scheduled_sessions, with_modal_url='view_popup'
        )
        rooms_list = {
            room.scoped_name: {'title': room.title, 'bgcolor': room.bgcolor}
            for room in self.obj.rooms
        }
        return {
            'project': self.obj,
            'from_date': (
                localize_timezone(
                    self.obj.schedule_start_at, tz=self.obj.timezone
                ).isoformat()
                if self.obj.schedule_start_at
                else None
            ),
            'to_date': (
                localize_timezone(
                    self.obj.schedule_end_at, tz=self.obj.timezone
                ).isoformat()
                if self.obj.schedule_start_at
                else None
            ),
            'sessions': scheduled_sessions_list,
            'timezone': self.obj.timezone.zone,
            'venues': [venue.current_access() for venue in self.obj.venues],
            'rooms': (
                rooms_list
                if len(rooms_list) > 0
                else {
                    self.obj.primary_venue.name: {
                        'title': self.obj.primary_venue.title,
                        'bgcolor': "CCCCCC",
                    }
                }
                if self.obj.primary_venue is not None
                else []
            ),
            'schedule': schedule_data(
                self.obj, with_slots=False, scheduled_sessions=scheduled_sessions_list
            ),
            'schedule_transition_form': schedule_transition_form,
            'project_save_form': project_save_form,
        }

    @route('subscribe')
    @render_with('schedule_subscribe.html.jinja2')
    @requires_roles({'reader'})
    def subscribe_schedule(self):
        return {'project': self.obj, 'venues': self.obj.venues, 'rooms': self.obj.rooms}

    @route('json')
    @cors('*')
    @requires_roles({'reader'})
    def schedule_json(self):
        scheduled_sessions_list = session_list_data(self.obj.scheduled_sessions)
        return jsonp(
            schedule=schedule_data(
                self.obj, with_slots=True, scheduled_sessions=scheduled_sessions_list
            ),
            venues=[venue.current_access() for venue in self.obj.venues],
            rooms=[room_data(room) for room in self.obj.rooms],
        )

    @route('ical')
    @requires_roles({'reader'})
    def schedule_ical(self):
        cal = Calendar()
        cal.add('prodid', "-//HasGeek//NONSGML Funnel//EN")
        cal.add('version', '2.0')
        cal.add('name', self.obj.title)
        cal.add('x-wr-calname', self.obj.title)
        cal.add('summary', self.obj.title)
        cal.add('description', self.obj.tagline)
        cal.add('x-wr-caldesc', self.obj.tagline)
        cal.add('timezone-id', self.obj.timezone.zone)
        cal.add('x-wr-timezone', self.obj.timezone.zone)
        cal.add('refresh-interval;value=duration', 'PT12H')
        cal.add('x-published-ttl', 'PT12H')
        for session in self.obj.scheduled_sessions:
            cal.add_component(session_ical(session))
        return Response(
            cal.to_ical(),
            mimetype='text/calendar',
            headers={
                'Content-Disposition': f'attachment;filename='
                f'"{self.obj.profile.name}-{self.obj.name}.ics"'
            },
        )

    @route('edit')
    @render_with('schedule_edit.html.jinja2')
    @requires_login
    @requires_roles({'editor'})
    def edit_schedule(self):
        schedule_transition_form = ProjectScheduleTransitionForm(obj=self.obj)
        proposals = {
            'unscheduled': [
                {'title': proposal.title, 'modal_url': proposal.url_for('schedule')}
                for proposal in self.obj.proposals_all.filter(
                    Proposal.state.CONFIRMED
                ).order_by(Proposal.title)
                if not proposal.state.SCHEDULED
            ],
            'scheduled': session_list_data(
                self.obj.scheduled_sessions, with_modal_url='edit', with_delete_url=True
            ),
        }
        return {
            'project': self.obj,
            'proposals': proposals,
            'from_date': (
                localize_timezone(
                    self.obj.schedule_start_at, tz=self.obj.timezone
                ).isoformat()
                if self.obj.schedule_start_at
                else None
            ),
            'to_date': (
                localize_timezone(
                    self.obj.schedule_end_at, tz=self.obj.timezone
                ).isoformat()
                if self.obj.schedule_start_at
                else None
            ),
            'timezone': self.obj.timezone.zone,
            'venues': [venue.current_access() for venue in self.obj.venues],
            'rooms': {
                room.scoped_name: {
                    'title': room.title,
                    'vtitle': room.venue.title + " - " + room.title,
                    'bgcolor': room.bgcolor,
                }
                for room in self.obj.rooms
            },
            'schedule_transition_form': schedule_transition_form,
        }

    @route('update', methods=['POST'])
    @render_with('schedule_edit.html.jinja2')
    @requires_login
    @requires_roles({'editor'})
    @requestargs(('sessions', json.loads))
    def update_schedule(self, sessions):
        for session in sessions:
            try:
                s = Session.query.filter_by(
                    project=self.obj, url_id=session['id']
                ).one()
                s.start_at = session['start_at']
                s.end_at = session['end_at']
                db.session.commit()
            except NoResultFound:
                current_app.logger.error(
                    '%s schedule update error: session = %s',
                    project=self.obj.name,
                    session=session,
                )
        return jsonify(status=True)


@route('/<project>/schedule', subdomain='<profile>')
class FunnelProjectScheduleView(ProjectScheduleView):
    pass


ProjectScheduleView.init_app(app)
FunnelProjectScheduleView.init_app(funnelapp)


@VenueRoom.views('schedule')
@route('/<profile>/<project>/schedule/<venue>/<room>')
class ScheduleVenueRoomView(VenueRoomViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('ical')
    @requires_permission('view')
    def schedule_room_ical(self):
        cal = Calendar()
        cal.add('prodid', "-//HasGeek//NONSGML Funnel//EN"),
        cal.add('version', "2.0")
        cal.add(
            'name',
            f'{self.obj.venue.project.title} @ '
            f'{self.obj.venue.title} / {self.obj.title}',
        )
        cal.add(
            'x-wr-calname',
            f'{self.obj.venue.project.title} @ '
            f'{self.obj.venue.title} / {self.obj.title}',
        )
        cal.add(
            'summary',
            f'{self.obj.venue.project.title} @ '
            f'{self.obj.venue.title} / {self.obj.title}',
        )
        cal.add('timezone-id', self.obj.venue.project.timezone.zone)
        cal.add('x-wr-timezone', self.obj.venue.project.timezone.zone)
        cal.add('refresh-interval;value=duration', 'PT12H')
        cal.add('x-published-ttl', 'PT12H')

        for session in self.obj.scheduled_sessions:
            cal.add_component(session_ical(session))
        return Response(
            cal.to_ical(),
            mimetype='text/calendar',
            headers={
                'Content-Disposition': 'attachment;filename="'
                + self.obj.venue.project.profile.name
                + '-'
                + self.obj.venue.project.name
                + '-'
                + self.obj.venue.name
                + '-'
                + self.obj.name
                + '.ics"'
            },
        )

    @route('updates')
    @render_with('room_updates.html.jinja2')
    @requires_permission('view')
    def updates(self):
        now = utcnow()
        current_session = Session.query.filter(
            Session.start_at <= now,
            Session.end_at >= now,
            Session.project == self.obj.venue.project,
            db.or_(Session.venue_room == self.obj, Session.is_break == True),  # NOQA
        ).first()
        next_session = (
            Session.query.filter(
                Session.start_at > now,
                db.or_(
                    Session.venue_room == self.obj, Session.is_break == True
                ),  # NOQA
                Session.project == self.obj.venue.project,
            )
            .order_by(Session.start_at)
            .first()
        )
        if current_session:
            current_session.start_at = localize_date(
                current_session.start_at, to_tz=self.obj.venue.project.timezone
            )
            current_session.end_at = localize_date(
                current_session.end_at, to_tz=self.obj.venue.project.timezone
            )
        nextdiff = None
        if next_session:
            next_session.start_at = localize_date(
                next_session.start_at, to_tz=self.obj.venue.project.timezone
            )
            next_session.end_at = localize_date(
                next_session.end_at, to_tz=self.obj.venue.project.timezone
            )
            nextdiff = next_session.start_at.date() - now.date()
            nextdiff = nextdiff.total_seconds() / 86400
        return {
            'room': self.obj,
            'current_session': current_session,
            'next_session': next_session,
            'nextdiff': nextdiff,
        }


@route('/<project>/schedule/<venue>/<room>', subdomain='<profile>')
class FunnelScheduleVenueRoomView(ScheduleVenueRoomView):
    pass


ScheduleVenueRoomView.init_app(app)
FunnelScheduleVenueRoomView.init_app(funnelapp)
