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

@app.route('/<space>/<proposal>/create_session', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
	(ProposalSpace, {'name': 'space'}, 'space'),
	(Proposal, {'url_name': 'proposal'}, 'proposal'),
    permission=('siteadmin'), addlperms=lastuser.permissions)
def session_create(proposal, space):
	form = SessionForm()
	venues = [venue.id for venue in Venue.query.filter_by(proposal_space=space).all()]
	rooms = VenueRoom.query.filter(VenueRoom.id.in_(venues)).all()
	rooms = [(room.id, __("{venue} - {room}".format(venue=room.venue.name, room=room.name))) for room in rooms]
	form.venue_room_id.choices = rooms
	if request.method == 'GET':
		form.description.data = proposal.description
		form.speaker_bio.data = proposal.bio
		form.title.data = proposal.title
		return render_template('session_form.html', form=form, formid='session_new', space=space, proposal=proposal)
	if form.validate_on_submit():
		session = Session()
		session.parent = space
		session.proposal = proposal
		form.start.data = datetime.fromtimestamp(int(form.start.data)/1000)
		form.end.data = datetime.fromtimestamp(int(form.end.data)/1000)
		form.populate_obj(session)
		session.venue_room_id = request.form.get('venue_room_id')
		session.make_id()
		session.make_name()
		db.session.add(session)
		db.session.commit()
		data = dict(id=session.id, title=session.title, modal_url=None)
		return jsonify(status=True, data=json.dumps(data))
	return jsonify(
		status=False,
		form=render_template('session_form.html', form=form, formid='session_new', space=space, proposal=proposal))
