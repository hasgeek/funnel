# -*- coding: utf-8 -*-

from baseframe import _
from datetime import datetime
from flask import request, render_template, jsonify
from coaster.views import load_models

from .. import app, lastuser
from ..models import db, Proposal, ProposalSpace, Session
from ..forms import SessionForm


def rooms_list(space):
    return [(0, _("Select Room"))] + [
        (room.id, "{venue} - {room}".format(venue=room.venue.title, room=room.title)) for room in space.rooms]


def session_form(space, proposal=None, session=None):
    if session:
        form = SessionForm(obj=session, model=Session)
    else:
        form = SessionForm()
    form.venue_room_id.choices = rooms_list(space)
    if not (session or proposal):
        form.is_break.data = True
    if request.method == 'GET':
        if proposal:
            form.description.data = proposal.description
            form.speaker_bio.data = proposal.bio
            form.title.data = proposal.title
        return render_template('session_form.html', form=form, formid='session_form')
    if form.validate_on_submit():
        new = False
        if not session:
            new = True
            session = Session()
        if proposal:
            session.proposal = proposal
        form.start.data = datetime.fromtimestamp(int(form.start.data)/1000)
        form.end.data = datetime.fromtimestamp(int(form.end.data)/1000)
        form.populate_obj(session)
        if session.venue_room_id == 0:
            session.venue_room_id = None
        if new:
            session.parent = space
            session.make_id()  # FIXME: This should not be required
            session.make_name()
            db.session.add(session)
        db.session.commit()
        data = dict(
            id=session.id, title=session.title,venue_room_id=session.venue_room_id,
            is_break=session.is_break, modal_url=session.url_for('edit'))
        return jsonify(status=True, data=data)
    return jsonify(
        status=False,
        form=render_template('session_form.html', form=form, formid='session_new'))


@app.route('/<space>/sessions/new', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    permission=('new-session', 'siteadmin'), addlperms=lastuser.permissions)
def session_new(space):
    return session_form(space)


@app.route('/<space>/<proposal>/schedule', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Proposal, {'url_name': 'proposal'}, 'proposal'),
    permission=('new-session', 'siteadmin'), addlperms=lastuser.permissions)
def proposal_schedule(space, proposal):
    return session_form(space, proposal=proposal)


@app.route('/<space>/<session>/editsession', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (Session, {'url_name': 'session'}, 'session'),
    permission=('edit-session', 'siteadmin'), addlperms=lastuser.permissions)
def session_edit(space, session):
    return session_form(space, session=session)
