# -*- coding: utf-8 -*-

from flask import g, render_template, redirect, jsonify
from datetime import datetime
from coaster.views import jsonp, load_model
from .. import funnelapp, app
from ..models import Profile, ProposalSpace, Proposal
from .space import space_data


@funnelapp.route('/')
def index():
    g.profile = None
    g.permissions = []
    spaces = ProposalSpace.fetch_sorted().filter(ProposalSpace.profile != None).all()
    return render_template('index.html.jinja2', spaces=spaces)


@funnelapp.route('/api/whoami')
def whoami():
    if g.user:
        return jsonify(message="Hey {0}!".format(g.user.fullname), code=200)
    else:
        return jsonify(message="Hmm, so who _are_ you?", code=401)


@funnelapp.route('/json')
def all_spaces_json():
    g.profile = None
    g.permissions = []
    spaces = ProposalSpace.fetch_sorted().filter(ProposalSpace.profile != None).all()
    return jsonp(spaces=map(space_data, spaces))


@funnelapp.route('/json', subdomain='<profile>')
@load_model(Profile, {'name': 'profile'}, 'g.profile', permission='view')
def spaces_json(profile):
    spaces = ProposalSpace.fetch_sorted().filter_by(profile=profile).all()
    return jsonp(spaces=map(space_data, spaces))


@funnelapp.route('/', subdomain='<profile>')
@load_model(Profile, {'name': 'profile'}, 'g.profile', permission='view')
def profile_view(profile):
    spaces = ProposalSpace.fetch_sorted().filter(
        ProposalSpace.profile == profile, ProposalSpace.parent_space == None
    ).all()
    return render_template('index.html.jinja2', spaces=spaces)


# Legacy routes for funnel to talkfunnel migration
# Figure out how to restrict these routes to just the funnel.hasgeek.com domain

@funnelapp.route('/<space>/')
@load_model(ProposalSpace, {'legacy_name': 'space'}, 'space')
def space_redirect(space):
    return redirect(space.url_for())


@funnelapp.route('/<space>/json')
@load_model(ProposalSpace, {'legacy_name': 'space'}, 'space')
def space_redirect_json(space):
    return redirect(space.url_for('json'))


@funnelapp.route('/<space>/csv')
@load_model(ProposalSpace, {'legacy_name': 'space'}, 'space')
def space_redirect_csv(space):
    return redirect(space.url_for('csv'))


@funnelapp.route('/<space>/<int:id>-<name>')
@funnelapp.route('/<space>/<int:id>')
@load_model(Proposal, {'id': 'id'}, 'proposal')
def proposal_redirect(proposal):
    return redirect(proposal.url_for())
