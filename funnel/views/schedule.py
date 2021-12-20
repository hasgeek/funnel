from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, cast

from sqlalchemy.orm.exc import NoResultFound

from flask import Response, current_app, json, jsonify

from icalendar import Alarm, Calendar, Event, vCalAddress, vText
from pytz import utc

from baseframe import _, localize_timezone
from coaster.utils import utcnow
from coaster.views import (
    ModelView,
    UrlChangeCheck,
    UrlForView,
    render_with,
    requestargs,
    requires_roles,
    route,
)

from .. import app
from ..models import Project, Proposal, Rsvp, Session, VenueRoom, db
from ..typing import ReturnRenderWith, ReturnView
from .helpers import localize_date
from .login_session import requires_login
from .mixins import ProjectViewMixin, VenueRoomViewMixin

# TODO: Replace the arbitrary dicts in the `_data` functions with dataclasses


def session_data(
    session: Session, with_modal_url: Optional[str] = None, with_delete_url=False
):
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
        'url': session.url_for(_external=True),
        'proposal_url': (
            session.proposal.url_for(_external=True) if session.proposal else None
        ),
        'proposal': session.proposal.uuid_b58 if session.proposal else None,
        'room': (session.venue_room.scoped_name if session.venue_room else None),
    }
    if with_modal_url:
        data.update({'modal_url': session.url_for(with_modal_url)})
    if with_delete_url:
        data.update({'delete_url': session.url_for('delete')})
    return data


def session_list_data(
    sessions: List[Session], with_modal_url=False, with_delete_url=False
):
    return [
        session_data(session, with_modal_url, with_delete_url) for session in sessions
    ]


def schedule_data(
    project: Project, with_slots=True, scheduled_sessions=None
) -> List[dict]:
    scheduled_sessions = scheduled_sessions or session_list_data(
        project.scheduled_sessions
    )
    data: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
    start_end_datetime: Dict[str, dict] = defaultdict(dict)
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
        daydata: Dict[str, Any] = {'date': day, 'slots': []}
        daydata['start_at'] = start_end_datetime[day]['start_at'].isoformat()
        daydata['end_at'] = start_end_datetime[day]['end_at'].isoformat()
        for slot in sorted(data[day]):
            daydata['slots'].append({'slot': slot, 'sessions': data[day][slot]})
        schedule.append(daydata)
    return schedule


def schedule_ical(project: Project, rsvp: Optional[Rsvp] = None):
    cal = Calendar()
    cal.add('prodid', "-//HasGeek//NONSGML Funnel//EN")
    cal.add('version', '2.0')
    cal.add('name', project.title)
    cal.add('x-wr-calname', project.title)
    cal.add('summary', project.title)
    cal.add('description', project.tagline)
    cal.add('x-wr-caldesc', project.tagline)
    cal.add('timezone-id', project.timezone.zone)
    cal.add('x-wr-timezone', project.timezone.zone)
    cal.add('refresh-interval;value=duration', 'PT12H')
    cal.add('x-published-ttl', 'PT12H')
    for session in project.scheduled_sessions:
        cal.add_component(session_ical(session, rsvp))
    if not project.scheduled_sessions and project.start_at:
        cal.add_component(
            # project_as_session does NOT return a Session instance, but since we are
            # ducktyping here, we use `cast` to tell mypy it's okay
            session_ical(cast(Session, project_as_session(project)), rsvp)
        )
    return cal.to_ical()


def project_as_session(project: Project) -> SimpleNamespace:
    """Return a Project as a namespace that resembles a Session object."""
    return SimpleNamespace(
        project=project,
        scheduled=True,
        uuid_b58=project.uuid_b58,
        created_at=project.published_at or project.created_at,
        updated_at=project.updated_at,
        title=project.title,
        description=project.description,
        start_at=project.start_at,
        start_at_localized=project.start_at_localized,
        end_at=project.end_at,
        end_at_localized=project.end_at_localized,
        location=f'{project.location} - {project.url_for(_external=True)}',
        venue_room=None,
        proposal=SimpleNamespace(labels=()),  # Proposal is used to get a permalink
        url_for=project.url_for,
    )


def session_ical(session: Session, rsvp: Optional[Rsvp] = None) -> Event:
    # This function is only called with scheduled sessions.
    # If for some reason it is used somewhere else and called with an unscheduled
    # session, this function should fail.
    if not session.scheduled:
        raise Exception(f"{session!r} is not scheduled")

    event = Event()
    event.add('summary', session.title)
    organizer = vCalAddress(f'MAILTO:no-reply@{current_app.config["DEFAULT_DOMAIN"]}')
    organizer.params['cn'] = vText(session.project.profile.title)
    event['organizer'] = organizer
    if rsvp:
        attendee = vCalAddress('MAILTO:' + str(rsvp.user_email()))
        attendee.params['RSVP'] = vText('TRUE') if rsvp.state.YES else vText('FALSE')
        attendee.params['cn'] = vText(rsvp.user.fullname)
        attendee.params['CUTYPE'] = vText('INDIVIDUAL')
        attendee.params['X-NUM-GUESTS'] = vText('0')
        event.add('attendee', attendee, encode=0)
    event.add(
        'uid', f'session/{session.uuid_b58}@{current_app.config["DEFAULT_DOMAIN"]}'
    )
    # Using localized timestamps will require a `VTIMEZONE` entry in the ics file
    # Using `session.start_at` without `astimezone` causes it to be localized to
    # local timezone. We need `astimezone(utc)` to ensure actual UTC timestamps.
    event.add('dtstart', session.start_at.astimezone(utc))
    event.add('dtend', session.end_at.astimezone(utc))
    event.add('dtstamp', utcnow())
    # Strangely, these two don't need localization with `astimezone`
    event.add('created', session.created_at)
    event.add('last-modified', session.updated_at)
    if session.location:
        event.add('location', session.location)
    if session.venue_room and session.venue_room.venue.has_coordinates:
        event.add('geo', session.venue_room.venue.coordinates)
    if session.description:
        event.add('description', session.description.text)
    if session.proposal:
        event.add('url', session.url_for(_external=True))
        if session.proposal.labels:
            event.add('categories', [label.title for label in session.proposal.labels])
    alarm = Alarm()
    alarm.add('trigger', timedelta(minutes=-5))
    alarm.add('action', 'display')
    if session.venue_room:
        desc = _("{session} in {venue} in 5 minutes").format(
            session=session.title, venue=session.venue_room.title
        )
    else:
        desc = _("{session} in 5 minutes").format(session=session.title)
    alarm.add('description', desc)
    event.add_component(alarm)
    return event


@Project.views('schedule')
@route('/<profile>/<project>/schedule')
class ProjectScheduleView(ProjectViewMixin, UrlChangeCheck, UrlForView, ModelView):
    @route('')
    @render_with('project_schedule.html.jinja2')
    @requires_roles({'reader'})
    def schedule(self) -> ReturnRenderWith:
        scheduled_sessions_list = session_list_data(
            self.obj.scheduled_sessions, with_modal_url='view_popup'
        )
        return {
            'project': self.obj.current_access(datasets=('primary', 'related')),
            'venues': [
                venue.current_access(datasets=('without_parent', 'related'))
                for venue in self.obj.venues
            ],
            'sessions': scheduled_sessions_list,
            'schedule': schedule_data(
                self.obj, with_slots=False, scheduled_sessions=scheduled_sessions_list
            ),
        }

    @route('subscribe')
    @render_with('schedule_subscribe.html.jinja2')
    @requires_roles({'reader'})
    def subscribe_schedule(self) -> ReturnRenderWith:
        return {'project': self.obj, 'venues': self.obj.venues, 'rooms': self.obj.rooms}

    @route('ical')
    @requires_roles({'reader'})
    def schedule_ical_download(self) -> ReturnView:
        return Response(
            schedule_ical(self.obj),
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
    def edit_schedule(self) -> ReturnRenderWith:
        proposals = {
            'unscheduled': [
                {
                    'title': proposal.title,
                    'modal_url': proposal.url_for('schedule'),
                    'speaker': proposal.first_user,
                    'user': proposal.user,
                    'labels': list(proposal.labels),
                }
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
                self.obj.start_at_localized.isoformat() if self.obj.start_at else None
            ),
            'to_date': (
                self.obj.end_at_localized.isoformat() if self.obj.end_at else None
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
        }

    @route('update', methods=['POST'])
    @requires_login
    @requires_roles({'editor'})
    @requestargs(('sessions', json.loads))
    def update_schedule(self, sessions) -> ReturnView:
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
                    '%s/%s schedule update error: no existing session matching %s',
                    self.obj.profile.name,
                    self.obj.name,
                    repr(session),
                )
        self.obj.update_schedule_timestamps()
        db.session.commit()
        return jsonify(status=True)


ProjectScheduleView.init_app(app)


@VenueRoom.views('schedule')
@route('/<profile>/<project>/schedule/<venue>/<room>')
class ScheduleVenueRoomView(VenueRoomViewMixin, UrlForView, ModelView):
    @route('ical')
    @requires_roles({'reader'})
    def schedule_room_ical(self) -> Response:
        cal = Calendar()
        cal.add('prodid', "-//Hasgeek//NONSGML Funnel//EN"),
        cal.add('version', "2.0")
        cal.add(
            'name',
            f"{self.obj.venue.project.title} @"
            f" {self.obj.venue.title} / {self.obj.title}",
        )
        cal.add(
            'x-wr-calname',
            f"{self.obj.venue.project.title} @"
            f" {self.obj.venue.title} / {self.obj.title}",
        )
        cal.add(
            'summary',
            f"{self.obj.venue.project.title} @"
            f" {self.obj.venue.title} / {self.obj.title}",
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
    @requires_roles({'reader'})
    def updates(self) -> ReturnRenderWith:
        now = utcnow()
        current_session = Session.query.filter(
            Session.start_at <= now,
            Session.end_at >= now,
            Session.project == self.obj.venue.project,
            db.or_(Session.venue_room == self.obj, Session.is_break.is_(True)),
        ).first()
        next_session = (
            Session.query.filter(
                Session.start_at > now,
                db.or_(Session.venue_room == self.obj, Session.is_break.is_(True)),
                Session.project == self.obj.venue.project,
            )
            .order_by(Session.start_at)
            .first()
        )
        if current_session is not None:
            current_session.start_at = localize_date(
                current_session.start_at, to_tz=self.obj.venue.project.timezone
            )
            current_session.end_at = localize_date(
                current_session.end_at, to_tz=self.obj.venue.project.timezone
            )
        nextdiff = None
        if next_session is not None:
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


ScheduleVenueRoomView.init_app(app)
