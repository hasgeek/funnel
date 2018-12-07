# -*- coding: utf-8 -*-

from baseframe import _
from flask import request, render_template, jsonify, redirect
from coaster.views import load_models, route, render_with, requires_permission, UrlForView, ModelView
from coaster.sqlalchemy import failsafe_add

from .helpers import localize_date
from .. import app, funnelapp, lastuser
from ..models import db, Profile, Proposal, ProposalRedirect, Project, ProjectRedirect, Session
from ..forms import SessionForm
from .mixins import ProjectViewMixin, SessionViewMixin


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
    @route('new')
    @lastuser.requires_login
    @requires_permission('new-session')
    def new_session(self):
        return session_form(self.obj)


@route('/<project>/sessions', subdomain='<profile>')
class FunnelProjectSessionView(ProjectSessionView):
    pass


ProjectSessionView.init_app(app)
FunnelProjectSessionView.init_app(funnelapp)


@app.route('/<profile>/<project>/<proposal>/schedule', methods=['GET', 'POST'])
@funnelapp.route('/<project>/<proposal>/schedule', methods=['GET', 'POST'], subdomain='<profile>')
@Proposal.is_url_for('schedule', profile='project.profile.name', project='project.name', proposal='url_name')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    ((Proposal, ProposalRedirect), {'url_name': 'proposal', 'project': 'project'}, 'proposal'),
    permission='new-session')
def proposal_schedule(profile, project, proposal):
    return session_form(project, proposal=proposal)


@route('/<profile>/<project>/<session>')
class SessionView(SessionViewMixin, UrlForView, ModelView):
    @route('viewsession')
    def view(self):
        return redirect(self.obj.project.url_for('schedule') + u"#" + self.obj.url_name, code=303)

    @route('viewsession-popup')
    @render_with('session_view_popup.html.jinja2')
    @requires_permission('view')
    def view_popup(self):
        return dict(session=self.obj, timezone=self.obj.project.timezone, localize_date=localize_date)

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



@route('/<project>/<session>', subdomain='<profile>')
class FunnelSessionView(SessionView):
    pass


SessionView.init_app(app)
FunnelSessionView.init_app(funnelapp)


# @app.route('/<profile>/<project>/<session>/viewsession-popup', methods=['GET'])
# @funnelapp.route('/<project>/<session>/viewsession-popup', methods=['GET'], subdomain='<profile>')
# @load_models(
#     (Profile, {'name': 'profile'}, 'g.profile'),
#     ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
#     (Session, {'url_name': 'session', 'project': 'project'}, 'session'),
#     permission='view')
# def session_view_popup(profile, project, session):
#     return dict(session=session, timezone=project.timezone, localize_date=localize_date)


# @app.route('/<profile>/<project>/<session>/editsession', methods=['GET', 'POST'])
# @funnelapp.route('/<project>/<session>/editsession', methods=['GET', 'POST'], subdomain='<profile>')
# @lastuser.requires_login
# @load_models(
#     (Profile, {'name': 'profile'}, 'g.profile'),
#     ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
#     (Session, {'url_name': 'session', 'project': 'project'}, 'session'),
#     permission='edit-session')
# def session_edit(profile, project, session):
#     return session_form(project, session=session)


# @app.route('/<profile>/<project>/<session>/deletesession', methods=['POST'])
# @funnelapp.route('/<project>/<session>/deletesession', methods=['POST'], subdomain='<profile>')
# @lastuser.requires_login
# @load_models(
#     (Profile, {'name': 'profile'}, 'g.profile'),
#     ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
#     (Session, {'url_name': 'session', 'project': 'project'}, 'session'),
#     permission='edit-session')
# def session_delete(profile, project, session):
#     modal_url = session.proposal.url_for('schedule') if session.proposal else None
#     if not session.proposal:
#         db.session.delete(session)
#     else:
#         session.make_unscheduled()
#     db.session.commit()
#     return jsonify(status=True, modal_url=modal_url)
