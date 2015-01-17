# -*- coding: utf-8 -*-

from baseframe import _
from flask import request, render_template, jsonify
from coaster.views import load_models

from .helpers import localize_date
from .. import app, lastuser
from ..models import db, Profile, Proposal, ProposalRedirect, ProposalSpace, ProposalSpaceRedirect, Session
from ..forms import SessionForm


def rooms_list(space):
    return [(u"", _("Select Room"))] + [
        (room.id, "{venue} - {room}".format(venue=room.venue.title, room=room.title)) for room in space.rooms]


def session_form(space, proposal=None, session=None):
    if session:
        form = SessionForm(obj=session, model=Session)
    else:
        form = SessionForm()
    form.venue_room_id.choices = rooms_list(space)
    if request.method == 'GET':
        if not (session or proposal):
            form.is_break.data = True
        if proposal:
            form.description.data = proposal.description
            form.speaker_bio.data = proposal.bio
            form.speaker.data = proposal.owner.fullname
            form.title.data = proposal.title
        return render_template('session_form.html', form=form, formid='session_form')
    if form.validate_on_submit():
        new = False
        if not session:
            new = True
            session = Session()
        if proposal:
            session.proposal = proposal
        form.populate_obj(session)
        if new:
            session.parent = space
            session.make_id()  # FIXME: This should not be required
            session.make_name()
            db.session.add(session)
        db.session.commit()
        data = dict(
            id=session.url_id, title=session.title, room_scoped_name=session.venue_room.scoped_name if session.venue_room else None,
            is_break=session.is_break, modal_url=session.url_for('edit'), delete_url=session.url_for('delete'),
            proposal_id=session.proposal_id)
        return jsonify(status=True, data=data)
    return jsonify(
        status=False,
        form=render_template('session_form.html', form=form, formid='session_new'))


@app.route('/<space>/sessions/new', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='new-session')
def session_new(profile, space):
    return session_form(space)


@app.route('/<space>/<proposal>/schedule', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    ((Proposal, ProposalRedirect), {'url_name': 'proposal', 'proposal_space': 'space'}, 'proposal'),
    permission='new-session')
def proposal_schedule(profile, space, proposal):
    return session_form(space, proposal=proposal)


@app.route('/<space>/<session>/viewsession-popup', methods=['GET'], subdomain='<profile>')
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Session, {'url_name': 'session', 'proposal_space': 'space'}, 'session'),
    permission='view')
def session_view_popup(profile, space, session):
    return render_template('session_view_popup.html', session=session, timezone=space.timezone, localize_date=localize_date)


@app.route('/<space>/<session>/editsession', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Session, {'url_name': 'session', 'proposal_space': 'space'}, 'session'),
    permission='edit-session')
def session_edit(profile, space, session):
    return session_form(space, session=session)


@app.route('/<space>/<session>/deletesession', methods=['POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (Session, {'url_name': 'session', 'proposal_space': 'space'}, 'session'),
    permission='edit-session')
def session_delete(profile, space, session):
    modal_url = session.proposal.url_for('schedule') if session.proposal else None
    db.session.delete(session)
    db.session.commit()
    return jsonify(status=True, modal_url=modal_url)
