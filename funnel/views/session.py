# -*- coding: utf-8 -*-

from baseframe import _
from flask import request, render_template, jsonify
from coaster.views import load_models
from coaster.sqlalchemy import failsafe_add

from .helpers import localize_date
from .. import app, funnelapp, lastuser
from ..models import db, Profile, Proposal, ProposalRedirect, Project, ProjectRedirect, Session
from ..forms import SessionForm


def rooms_list(project):
    return [(u"", _("Select Room"))] + [
        (room.id, u"{venue} - {room}".format(venue=room.venue.title, room=room.title)) for room in project.rooms]


def session_form(project, proposal=None, session=None):
    if session:
        form = SessionForm(obj=session, model=Session)
    else:
        form = SessionForm()
    form.venue_room_id.choices = rooms_list(project)
    if request.method == 'GET':
        if not (session or proposal):
            form.is_break.data = True
        if proposal:
            form.description.data = proposal.description
            form.speaker_bio.data = proposal.bio
            form.speaker.data = proposal.owner.fullname
            form.title.data = proposal.title
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
            session.make_id()  # FIXME: This should not be required
            session.make_name()
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


@app.route('/<profile>/<project>/sessions/new', methods=['GET', 'POST'])
@funnelapp.route('/<project>/sessions/new', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='new-session')
def session_new(profile, project):
    return session_form(project)


@app.route('/<profile>/<project>/<proposal>/schedule', methods=['GET', 'POST'])
@funnelapp.route('/<project>/<proposal>/schedule', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    ((Proposal, ProposalRedirect), {'url_name': 'proposal', 'project': 'project'}, 'proposal'),
    permission='new-session')
def proposal_schedule(profile, project, proposal):
    return session_form(project, proposal=proposal)


@app.route('/<profile>/<project>/<session>/viewsession-popup', methods=['GET'])
@funnelapp.route('/<project>/<session>/viewsession-popup', methods=['GET'], subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Session, {'url_name': 'session', 'project': 'project'}, 'session'),
    permission='view')
def session_view_popup(profile, project, session):
    return render_template('session_view_popup.html.jinja2', session=session, timezone=project.timezone, localize_date=localize_date)


@app.route('/<profile>/<project>/<session>/editsession', methods=['GET', 'POST'])
@funnelapp.route('/<project>/<session>/editsession', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Session, {'url_name': 'session', 'project': 'project'}, 'session'),
    permission='edit-session')
def session_edit(profile, project, session):
    return session_form(project, session=session)


@app.route('/<profile>/<project>/<session>/deletesession', methods=['POST'])
@funnelapp.route('/<project>/<session>/deletesession', methods=['POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (Session, {'url_name': 'session', 'project': 'project'}, 'session'),
    permission='edit-session')
def session_delete(profile, project, session):
    modal_url = session.proposal.url_for('schedule') if session.proposal else None
    db.session.delete(session)
    db.session.commit()
    return jsonify(status=True, modal_url=modal_url)
