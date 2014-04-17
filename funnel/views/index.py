# -*- coding: utf-8 -*-

from flask import render_template
from .. import app, lastuser
from ..models import Profile, ProposalSpace
from coaster.views import jsonp, load_model
from .space import space_data


@app.route('/')
def index():
    spaces = ProposalSpace.query.filter(ProposalSpace.status >= 1).filter(ProposalSpace.status <= 4).order_by(ProposalSpace.date.desc()).all()
    return render_template('index.html', spaces=spaces, siteadmin=lastuser.has_permission('siteadmin'))


@app.route('/json', subdomain='<profile>')
@load_model(Profile, {'name': 'profile'}, 'profile')
def spaces_json(profile):
	return jsonp(spaces=[space_data(space) for space in ProposalSpace.query.filter_by(profile=profile).all()])


@app.route('/', subdomain='<profile>')
@load_model(Profile, {'name': 'profile'}, 'profile')
def profile_view(profile):
    spaces = ProposalSpace.query.filter(ProposalSpace.profile == profile).filter(
        ProposalSpace.status >= 1).filter(ProposalSpace.status <= 4).order_by(ProposalSpace.date.desc()).all()
    return render_template('index.html', spaces=spaces, siteadmin=lastuser.has_permission('siteadmin'))
