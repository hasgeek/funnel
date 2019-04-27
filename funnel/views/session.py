# -*- coding: utf-8 -*-

from datetime import datetime
from baseframe import _
from flask import request, render_template, jsonify, abort
from coaster.views import route, render_with, requires_permission, UrlForView, ModelView, requestargs
from coaster.sqlalchemy import failsafe_add

from .helpers import localize_date
from .. import app, funnelapp, lastuser
from ..models import db, ProposalFeedback, Session, FEEDBACK_AUTH_TYPE
from ..forms import SessionForm
from .mixins import ProjectViewMixin, SessionViewMixin
from .decorators import legacy_redirect
from .schedule import session_data, session_list_data, date_js


def rooms_list(project):
    return [(u"", _("Select Room"))] + [
        (room.id, u"{venue} – {room}".format(venue=room.venue.title, room=room.title)) for room in project.rooms]


def session_form(project, proposal=None, session=None):
    # Look for any existing unscheduled session
    if proposal and not session:
        session = Session.for_proposal(proposal)

    if session:
        form = SessionForm(obj=session, model=Session)
    else:
        form = SessionForm()
        if proposal:
            form.description.data = proposal.description
            form.speaker_bio.data = proposal.bio
            form.speaker.data = proposal.owner.fullname
            form.title.data = proposal.title

    form.venue_room_id.choices = rooms_list(project)
    if request.method == 'GET':
        if not (session or proposal):
            form.is_break.data = True
        return render_template('session_form.html.jinja2', form=form, formid='session_form')
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
            session = failsafe_add(db.session, session, project_id=project.id, url_id=session.url_id)
        db.session.commit()
        data = dict(
            id=session.url_id, title=session.title, room_scoped_name=session.venue_room.scoped_name if session.venue_room else None,
            is_break=session.is_break, modal_url=session.url_for('edit'), delete_url=session.url_for('delete'),
            proposal_id=session.proposal_id)
        return jsonify(status=True, data=data)
    return jsonify(
        status=False,
        form=render_template('session_form.html.jinja2', form=form, formid='session_new'))


@route('/<profile>/<project>/sessions')
class ProjectSessionView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('new', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('new-session')
    def new_session(self):
        return session_form(self.obj)


@route('/<project>/sessions', subdomain='<profile>')
class FunnelProjectSessionView(ProjectSessionView):
    pass


ProjectSessionView.init_app(app)
FunnelProjectSessionView.init_app(funnelapp)


@route('/<profile>/<project>/schedule/<session>')
class SessionView(SessionViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('')
    @render_with('schedule.html.jinja2', json=True)
    def view(self):
        return dict(project=self.obj.project, active_session=session_data(self.obj, with_modal_url='view_popup'),
            from_date=date_js(self.obj.project.date), to_date=date_js(self.obj.project.date_upto),
            sessions=session_list_data(self.obj.project.scheduled_sessions, with_modal_url='view_popup'),
            timezone=self.obj.project.timezone.utcoffset(datetime.utcnow()).total_seconds(),
            venues=[venue.current_access() for venue in self.obj.project.venues],
            rooms=dict([(room.scoped_name, {'title': room.title, 'bgcolor': room.bgcolor}) for room in self.obj.project.rooms]))

    @route('viewsession-popup')
    @render_with('session_view_popup.html.jinja2')
    @requires_permission('view')
    def view_popup(self):
        return dict(session=self.obj, timezone=self.obj.project.timezone.zone, localize_date=localize_date)

    @route('editsession', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('edit-session')
    def edit(self):
        return session_form(self.obj.project, session=self.obj)

    @route('deletesession', methods=['POST'])
    @lastuser.requires_login
    @requires_permission('edit-session')
    def delete(self):
        modal_url = self.obj.proposal.url_for('schedule') if self.obj.proposal else None
        if not self.obj.proposal:
            db.session.delete(self.obj)
        else:
            self.obj.make_unscheduled()
        db.session.commit()
        return jsonify(status=True, modal_url=modal_url)

    @route('feedback', methods=['POST'])
    @requires_permission('view')
    @requestargs('id_type', 'userid', ('content', int), ('presentation', int), ('min_scale', int), ('max_scale', int))
    def feedback(self, id_type, userid, content, presentation, min_scale=0, max_scale=2):
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
        feedback = ProposalFeedback.query.filter_by(proposal=self.obj.proposal,
            auth_type=FEEDBACK_AUTH_TYPE.NOAUTH, id_type=id_type, userid=userid).first()
        if feedback is not None:
            return "Dupe\n", 403
        else:
            feedback = ProposalFeedback(proposal=self.obj.proposal,
                auth_type=FEEDBACK_AUTH_TYPE.NOAUTH, id_type=id_type, userid=userid,
                min_scale=min_scale, max_scale=max_scale, content=content, presentation=presentation)
            db.session.add(feedback)
            db.session.commit()
            return "Saved\n", 201


@route('/<project>/schedule/<session>', subdomain='<profile>')
class FunnelSessionView(SessionView):
    pass


SessionView.init_app(app)
FunnelSessionView.init_app(funnelapp)
