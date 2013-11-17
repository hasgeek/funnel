# -*- coding: utf-8 -*-

from baseframe import __
from datetime import datetime
from flask import request, render_template, jsonify
from coaster.views import load_models
from coaster.utils import make_name
import simplejson as json

from .space import ProposalSpace
from .. import app, lastuser
from ..models import db, Proposal, ProposalSpace, Session, Venue, VenueRoom
from ..forms import SessionForm

def rooms_list(space):
	rooms = [(room.id, __("{venue} - {room}".format(venue=room.venue.name, room=room.name))) for room in space.rooms]
	rooms = [(0, "Select Room")] + rooms
	return rooms

def session_form(space, proposal=None, session=None):
	if session:
		print session.url_name, session.venue_room_id
		form = SessionForm(obj=session, model=Session)
	else:
		form = SessionForm()
	rooms = rooms_list(space)
	form.venue_room_id.choices = rooms
	if not (session or proposal):
		form.is_break.data = True
	if form.is_break.data:
		form.description.validators = [];
		form.speaker_bio.validators = [];
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
			session.parent = space
			session.proposal = proposal
		form.start.data = datetime.fromtimestamp(int(form.start.data)/1000)
		form.end.data = datetime.fromtimestamp(int(form.end.data)/1000)
		form.populate_obj(session)
		session.venue_room_id = request.form.get('venue_room_id') if int(request.form.get('venue_room_id')) != 0 else None
		if new:
			session.make_id()
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
    permission=('siteadmin'), addlperms=lastuser.permissions)
def session_new(space):
	return session_form(space)

@app.route('/<space>/<proposal>/create_session', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
	(ProposalSpace, {'name': 'space'}, 'space'),
	(Proposal, {'url_name': 'proposal'}, 'proposal'),
    permission=('siteadmin'), addlperms=lastuser.permissions)
def session_create(space, proposal):
	return session_form(space, proposal=proposal)

@app.route('/<space>/<session>/editsession', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
	(ProposalSpace, {'name': 'space'}, 'space'),
	(Session, {'url_name': 'session'}, 'session'),
	permission=('siteadmin'), addlperms=lastuser.permissions)
def session_edit(space, session):
	return session_form(space, session=session)