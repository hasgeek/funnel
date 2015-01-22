# -*- coding: utf-8 -*-

from flask import g, render_template, redirect
from .. import app
from ..models import Profile, ProposalSpace, Proposal
from coaster.views import jsonp, load_model
from .space import space_data


@app.route('/')
def index():
    g.profile = None
    g.permissions = []
    spaces = ProposalSpace.query.filter_by(parent_space=None).filter(ProposalSpace.profile != None).filter(ProposalSpace.status >= 1).filter(ProposalSpace.status <= 4).order_by(ProposalSpace.date.desc()).all()  # NOQA
    return render_template('index.html', spaces=spaces)


@app.route('/json')
def all_spaces_json():
    g.profile = None
    g.permissions = []
    # FIXME: Only return active spaces
    return jsonp(spaces=[space_data(space) for space in ProposalSpace.query.filter(ProposalSpace.profile != None).order_by(ProposalSpace.date.desc()).all()])  # NOQA


@app.route('/json', subdomain='<profile>')
@load_model(Profile, {'name': 'profile'}, 'g.profile', permission='view')
def spaces_json(profile):
    # FIXME: Only return active spaces
    return jsonp(spaces=[space_data(space) for space in ProposalSpace.query.filter_by(profile=profile).order_by(ProposalSpace.date.desc()).all()])


@app.route('/', subdomain='<profile>')
@load_model(Profile, {'name': 'profile'}, 'g.profile', permission='view')
def profile_view(profile):
    spaces = ProposalSpace.query.filter(ProposalSpace.profile == profile).filter(
        ProposalSpace.status >= 1).filter(ProposalSpace.status <= 4).order_by(ProposalSpace.date.desc()).all()
    return render_template('index.html', spaces=spaces)


# Legacy routes for funnel to talkfunnel migration
# Figure out how to restrict these routes to just the funnel.hasgeek.com domain

@app.route('/<space>/')
@load_model(ProposalSpace, {'legacy_name': 'space'}, 'space')
def space_redirect(space):
    return redirect(space.url_for())


@app.route('/<space>/json')
@load_model(ProposalSpace, {'legacy_name': 'space'}, 'space')
def space_redirect_json(space):
    return redirect(space.url_for('json'))


@app.route('/<space>/csv')
@load_model(ProposalSpace, {'legacy_name': 'space'}, 'space')
def space_redirect_csv(space):
    return redirect(space.url_for('csv'))


@app.route('/<space>/<int:id>-<name>')
@app.route('/<space>/<int:id>')
@load_model(Proposal, {'id': 'id'}, 'proposal')
def proposal_redirect(proposal):
    return redirect(proposal.url_for())
