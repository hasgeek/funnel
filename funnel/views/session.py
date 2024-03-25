"""Views for timestamped sessions in a project."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import render_template, request

from baseframe import _
from coaster.sqlalchemy import failsafe_add
from coaster.views import ModelView, UrlChangeCheck, UrlForView, requires_roles, route

from .. import app
from ..auth import current_auth
from ..forms import SavedProjectForm, SavedSessionForm, SessionForm
from ..models import Account, Project, Proposal, SavedSession, Session, db
from ..proxies import request_wants
from ..typing import ReturnRenderWith, ReturnView
from .helpers import localize_date, render_redirect
from .login_session import requires_login
from .mixins import AccountCheckMixin, ProjectViewBase
from .schedule import schedule_data, session_data, session_list_data


def rooms_list(project: Project) -> list[tuple[str, str]]:
    if project.rooms:
        return [("", _("Select Room"))] + [
            (
                str(room.id),
                f"{room.venue.title} – {room.title}",
            )
            for room in project.rooms
        ]
    return []


def get_form_template(form: SessionForm) -> ReturnView:
    """Render Session form html."""
    form.form_nonce.data = form.form_nonce.get_default()
    form_template = render_template(
        'session_form.html.jinja2',
        form=form,
        formid='session_new',
        ref_id='session_form',
        title=_("Edit session"),
    )
    return form_template


def session_edit(
    project: Project,
    proposal: Proposal | None = None,
    session: Session | None = None,
) -> ReturnView:
    # Look for any existing unscheduled session
    if proposal is not None and session is None:
        session = Session.for_proposal(proposal)

    if session is not None:
        form = SessionForm(obj=session, model=Session)
    else:
        form = SessionForm()
        if proposal is not None:
            form.description.data = str(proposal.body)
            form.speaker.data = proposal.first_user.fullname
            form.title.data = proposal.title

    form.venue_room_id.choices = rooms_list(project)
    if not form.venue_room_id.choices:
        del form.venue_room_id
    if request.method == 'GET':
        if request_wants.html_in_json:
            return {'status': True, 'form': get_form_template(form)}
        return get_form_template(form)
    if form.validate_on_submit():
        new = False
        if session is None:
            new = True
            session = Session()
        if proposal is not None:
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
        if TYPE_CHECKING:  # FIXME: Needed for Mypy in pre-commit only, unclear why
            assert session is not None  # nosec B101
        session.project.update_schedule_timestamps()
        db.session.commit()
        if request_wants.html_in_json:
            data = {
                'id': session.url_id,
                'title': session.title,
                'speaker': session.speaker,
                'room_scoped_name': (
                    session.venue_room.scoped_name
                    if session.venue_room is not None
                    else None
                ),
                'is_break': session.is_break,
                'modal_url': session.url_for('edit'),
                'delete_url': session.url_for('delete'),
                'proposal_id': session.proposal_id,  # FIXME: Switch to UUID
            }
            # FIXME: Return ``status='ok'`` and ``edited=True``
            return {'status': True, 'data': data}
        return render_redirect(session.url_for('view'))
    if request_wants.html_in_json:
        return {
            # FIXME: Return ``status='ok'`` and ``edited=False``
            'status': False,
            'form': get_form_template(form),
        }
    return get_form_template(form)


@Project.views('session_new')
@route('/<account>/<project>/sessions', init_app=app)
class ProjectSessionView(ProjectViewBase):
    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'editor'})
    def new_session(self) -> ReturnView:
        return session_edit(self.obj)


@Session.views('main')
@route('/<account>/<project>/schedule/<session>', init_app=app)
class SessionView(AccountCheckMixin, UrlChangeCheck, UrlForView, ModelView[Session]):
    route_model_map = {
        'account': 'project.account.urlname',
        'project': 'project.name',
        'session': 'url_name_uuid_b58',
    }
    SavedProjectForm = SavedProjectForm

    def loader(self, account: str, project: str, session: str) -> Session:
        return (
            Session.query.join(Project, Session.project_id == Project.id)
            .join(Account, Project.account)
            .filter(Session.url_name_uuid_b58 == session)
            .first_or_404()
        )

    def post_init(self) -> None:
        self.account = self.obj.project.account

    @property
    def project_currently_saved(self) -> bool:
        return self.obj.project.is_saved_by(current_auth.user)

    @route('')
    @route('viewsession-popup')  # Legacy route, will be auto-redirected to base URL
    # @requires_roles({'reader'})
    def view(self) -> ReturnView:
        if request_wants.html_fragment:
            return render_template(
                'session_view_popup.html.jinja2',
                session=self.obj.current_access(),
                timezone=self.obj.project.timezone.zone,
                localize_date=localize_date,
            )
        scheduled_sessions_list = session_list_data(
            self.obj.project.scheduled_sessions, with_modal_url='view'
        )
        return render_template(
            'project_schedule.html.jinja2',
            project=self.obj.project.current_access(
                datasets=('without_parent', 'related')
            ),
            from_date=(
                start_at.isoformat()
                if (start_at := self.obj.project.start_at_localized)
                else None
            ),
            to_date=(
                end_at.isoformat()
                if (end_at := self.obj.project.end_at_localized)
                else None
            ),
            active_session=session_data(self.obj, with_modal_url='view'),
            sessions=scheduled_sessions_list,
            timezone=self.obj.project.timezone.zone,
            venues=[
                venue.current_access(datasets=('without_parent', 'related'))
                for venue in self.obj.project.venues
            ],
            rooms={
                room.scoped_name: {'title': room.title, 'bgcolor': room.bgcolor}
                for room in self.obj.project.rooms
            },
            schedule=schedule_data(
                self.obj.project,
                with_slots=False,
                scheduled_sessions=scheduled_sessions_list,
            ),
        )

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'project_editor'})
    def edit(self) -> ReturnView:
        return session_edit(self.obj.project, session=self.obj)

    @route('delete', methods=['POST'])
    @requires_login
    @requires_roles({'project_editor'})
    def delete(self) -> ReturnView:
        modal_url = (
            self.obj.proposal.url_for('schedule')
            if self.obj.proposal is not None
            else None
        )
        if self.obj.proposal is None:
            db.session.delete(self.obj)
        else:
            self.obj.make_unscheduled()
        db.session.commit()
        self.obj.project.update_schedule_timestamps()
        db.session.commit()
        if self.obj.project.features.schedule_no_sessions():
            # FIXME: return 'status': 'ok'
            return {
                'status': True,
                'modal_url': modal_url,
                'message': _(
                    "This project will not be listed as it has no sessions in the"
                    " schedule"
                ),
            }
        return {'status': True, 'modal_url': modal_url}

    @route('save', methods=['POST'])
    @requires_login
    # @requires_roles({'reader'})
    def save(self) -> ReturnRenderWith:
        form = SavedSessionForm()
        created = False
        if form.validate_on_submit():
            session_save = SavedSession.query.filter_by(
                account=current_auth.user, session=self.obj
            ).first()
            if form.save.data:
                if session_save is None:
                    session_save = SavedSession(
                        account=current_auth.user, session=self.obj
                    )
                    created = True
                    form.populate_obj(session_save)
                    db.session.commit()
            else:
                if session_save is not None:
                    db.session.delete(session_save)
                    db.session.commit()
            return {'status': 'ok'}, 201 if created else 200
        return {
            'status': 'error',
            'error': 'session_save_form_invalid',
            'error_description': _("Something went wrong, please reload and try again"),
        }, 400
