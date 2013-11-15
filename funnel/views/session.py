# -*- coding: utf-8 -*-

from flask import request, render_template
from coaster.views import load_models

from .space import ProposalSpace
from .. import app, lastuser
from ..models import db, Proposal, ProposalSpace, Session
from ..forms import SessionForm

@app.route('/<space>/session/<proposal>/create', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
	(ProposalSpace, {'name': 'space'}, 'space'),
	(Proposal, {'url_name': 'proposal'}, 'proposal'),
    permission=('siteadmin'), addlperms=lastuser.permissions)
def session_create(proposal, space):
	form = SessionForm()
	if request.method == 'GET':
		form.description.data = proposal.description
		form.speaker_bio.data = proposal.bio
	if form.validate_on_submit():
		session = Session()
		session.parent = space
		session.proposal = proposal
		form.populate_obj(session)


	return render_template('session_new.html', form=form, formid='session_new', space=space, proposal=proposal)
