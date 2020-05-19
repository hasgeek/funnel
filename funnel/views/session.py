from flask import abort, jsonify, redirect, render_template, request

from baseframe import _, localize_timezone, request_is_xhr
from coaster.auth import current_auth
from coaster.sqlalchemy import failsafe_add
from coaster.views import (
    ModelView,
    UrlForView,
    render_with,
    requestargs,
    requires_permission,
    requires_roles,
    route,
)

from .. import app, funnelapp
from ..forms import SavedProjectForm, SavedSessionForm, SessionForm
from ..models import (
    FEEDBACK_AUTH_TYPE,
    Project,
    ProposalFeedback,
    SavedSession,
    Session,
    db,
)
from ..utils import strip_null
from .decorators import legacy_redirect
from .helpers import localize_date, requires_login
from .mixins import ProjectViewMixin, SessionViewMixin
from .schedule import schedule_data, session_data, session_list_data


def rooms_list(project):
    if project.rooms:
        return [("", _("Select Room"))] + [
            (
                room.id,
                "{venue} – {room}".format(venue=room.venue.title, room=room.title),
            )
            for room in project.rooms
        ]
    return []


def session_form(project, proposal=None, session=None):
    # Look for any existing unscheduled session
    if proposal and not session:
        session = Session.for_proposal(proposal)

    if session:
        form = SessionForm(obj=session, model=Session)
    else:
        form = SessionForm()
        if proposal:
            form.description.data = proposal.outline
            form.speaker_bio.data = proposal.bio
            form.speaker.data = proposal.owner.fullname
            form.title.data = proposal.title

    form.venue_room_id.choices = rooms_list(project)
    if not form.venue_room_id.choices:
        del form.venue_room_id
    if request.method == 'GET':
        if not (session or proposal):
            form.is_break.data = True
        return render_template(
            'session_form.html.jinja2',
            form=form,
            formid='session_form',
            title=_("Edit session"),
        )
    if form.validate_on_submit():
        new = False
        if not session:
            new = True
            session = Session()
        if proposal:
            session.proposal = proposal
        form.populate_obj(session)
        if new:
            session.parent = project
            if session.proposal:
                session = failsafe_add(
                    db.session,
                    session,
                    project_id=project.id,
                    proposal_id=session.proposal_id,
                )
            else:
                db.session.add(session)
        db.session.commit()
        if request_is_xhr():
            data = {
                'id': session.url_id,
                'title': session.title,
                'room_scoped_name': (
                    session.venue_room.scoped_name if session.venue_room else None
                ),
                'is_break': session.is_break,
                'modal_url': session.url_for('edit'),
                'delete_url': session.url_for('delete'),
                'proposal_id': session.proposal_id,  # FIXME: Switch to UUID
            }
            return jsonify(status=True, data=data)
        else:
            return redirect(session.url_for('view'))
    return jsonify(
        status=False,
        form=render_template(
            'session_form.html.jinja2',
            form=form,
            formid='session_new',
            title=_("Edit session"),
        ),
    )


@Project.views('session_new')
@route('/<profile>/<project>/sessions')
class ProjectSessionView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'editor'})
    def new_session(self):
        return session_form(self.obj)


@route('/<project>/sessions', subdomain='<profile>')
class FunnelProjectSessionView(ProjectSessionView):
    pass


ProjectSessionView.init_app(app)
FunnelProjectSessionView.init_app(funnelapp)


@Session.views('main')
@route('/<profile>/<project>/schedule/<session>')
class SessionView(SessionViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('')
    @render_with('schedule.html.jinja2', json=True)
    def view(self):
        project_save_form = SavedProjectForm()
        scheduled_sessions_list = session_list_data(
            self.obj.project.scheduled_sessions, with_modal_url='view_popup'
        )
        return {
            'project': self.obj.project,
            'from_date': (
                localize_timezone(
                    self.obj.project.schedule_start_at, tz=self.obj.project.timezone
                ).isoformat()
                if self.obj.project.schedule_start_at
                else None
            ),
            'to_date': (
                localize_timezone(
                    self.obj.project.schedule_end_at, tz=self.obj.project.timezone
                ).isoformat()
                if self.obj.project.schedule_end_at
                else None
            ),
            'active_session': session_data(self.obj, with_modal_url='view_popup'),
            'sessions': scheduled_sessions_list,
            'timezone': self.obj.project.timezone.zone,
            'venues': [venue.current_access() for venue in self.obj.project.venues],
            'rooms': {
                room.scoped_name: {'title': room.title, 'bgcolor': room.bgcolor}
                for room in self.obj.project.rooms
            },
            'schedule': schedule_data(
                self.obj, with_slots=False, scheduled_sessions=scheduled_sessions_list
            ),
            'project_save_form': project_save_form,
        }

    @route('viewsession-popup')
    @render_with('session_view_popup.html.jinja2')
    @requires_permission('view')
    def view_popup(self):
        return {
            'session': self.obj,
            'timezone': self.obj.project.timezone.zone,
            'localize_date': localize_date,
        }

    @route('editsession', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('edit-session')
    def edit(self):
        return session_form(self.obj.project, session=self.obj)

    @route('deletesession', methods=['POST'])
    @requires_login
    @requires_permission('edit-session')
    def delete(self):
        modal_url = self.obj.proposal.url_for('schedule') if self.obj.proposal else None
        if not self.obj.proposal:
            db.session.delete(self.obj)
        else:
            self.obj.make_unscheduled()
        db.session.commit()
        if self.obj.project.features.schedule_no_sessions():
            return jsonify(
                status=True,
                modal_url=modal_url,
                msg=_(
                    "This project will not be listed as it has no sessions in the "
                    "schedule"
                ),
            )
        return jsonify(status=True, modal_url=modal_url)

    @route('feedback', methods=['POST'])
    @requires_permission('view')
    @requestargs(
        ('id_type', strip_null),
        ('userid', strip_null),
        ('content', int),
        ('presentation', int),
        ('min_scale', int),
        ('max_scale', int),
    )
    def feedback(
        self, id_type, userid, content, presentation, min_scale=0, max_scale=2
    ):
        if not self.obj.proposal:
            abort(400)
        # Process feedback
        if not min_scale <= content <= max_scale:
            abort(400)
        if not min_scale <= presentation <= max_scale:
            abort(400)
        if id_type not in ('email', 'deviceid'):
            abort(400)

        # Was feedback already submitted?
        feedback = ProposalFeedback.query.filter_by(
            proposal=self.obj.proposal,
            auth_type=FEEDBACK_AUTH_TYPE.NOAUTH,
            id_type=id_type,
            userid=userid,
        ).first()
        if feedback is not None:
            return "Dupe\n", 403
        else:
            feedback = ProposalFeedback(
                proposal=self.obj.proposal,
                auth_type=FEEDBACK_AUTH_TYPE.NOAUTH,
                id_type=id_type,
                userid=userid,
                min_scale=min_scale,
                max_scale=max_scale,
                content=content,
                presentation=presentation,
            )
            db.session.add(feedback)
            db.session.commit()
            return "Saved\n", 201

    @route('save', methods=['POST'])
    @render_with(json=True)
    @requires_login
    @requires_permission('view')
    def save(self):
        form = SavedSessionForm()
        if form.validate_on_submit():
            session_save = SavedSession.query.filter_by(
                user=current_auth.user, session=self.obj
            ).first()
            if form.save.data:
                if session_save is None:
                    session_save = SavedSession(
                        user=current_auth.user, session=self.obj
                    )
                    form.populate_obj(session_save)
                    db.session.commit()
            else:
                if session_save is not None:
                    db.session.delete(session_save)
                    db.session.commit()
            return {'status': 'ok'}
        else:
            return (
                {
                    'status': 'error',
                    'error': 'session_save_form_invalid',
                    'error_description': _(
                        "Something went wrong, please reload and try again"
                    ),
                },
                400,
            )
        return redirect(self.obj.url_for(), code=303)


@route('/<project>/schedule/<session>', subdomain='<profile>')
class FunnelSessionView(SessionView):
    pass


SessionView.init_app(app)
FunnelSessionView.init_app(funnelapp)
