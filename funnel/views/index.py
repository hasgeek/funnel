# -*- coding: utf-8 -*-

from flask import g, render_template, redirect, jsonify
from coaster.views import jsonp, load_model, render_with
from .. import app, funnelapp
from ..models import Profile, ProposalSpace, Proposal
from .space import space_data


def index_jsonify(data):
    return jsonify(spaces=[d for d in [dict(s.current_access()) for s in data['spaces']] if d])


@app.route('/')
@render_with({'text/html': 'index.html.jinja2', 'application/json': index_jsonify})
def index():
    g.profile = None
    g.permissions = []
    spaces = ProposalSpace.fetch_sorted().filter(ProposalSpace.profile != None).all()
    return {'spaces': spaces}


@funnelapp.route('/', endpoint='index')
@render_with({'text/html': 'funnelindex.html.jinja2', 'application/json': index_jsonify})
def funnelindex():
    g.profile = None
    g.permissions = []
    spaces = ProposalSpace.fetch_sorted().filter(ProposalSpace.profile != None).all()
    return {'spaces': spaces}


@app.route('/api/whoami')
@funnelapp.route('/api/whoami')
def whoami():
    if g.user:
        return jsonify(message="Hey {0}!".format(g.user.fullname), code=200)
    else:
        return jsonify(message="Hmm, so who _are_ you?", code=401)


@app.route('/json')
@funnelapp.route('/json')
def all_spaces_json():
    g.profile = None
    g.permissions = []
    spaces = ProposalSpace.fetch_sorted().filter(ProposalSpace.profile != None).all()
    return jsonp(spaces=map(space_data, spaces))


@app.route('/<profile>/json')
@funnelapp.route('/json', subdomain='<profile>')
@load_model(Profile, {'name': 'profile'}, 'g.profile', permission='view')
def spaces_json(profile):
    spaces = ProposalSpace.fetch_sorted().filter_by(profile=profile).all()
    return jsonp(spaces=map(space_data, spaces))


@app.route('/<profile>/')
@funnelapp.route('/', subdomain='<profile>')
@load_model(Profile, {'name': 'profile'}, 'g.profile', permission='view')
def profile_view(profile):
    return render_template('index.html.jinja2', spaces=profile.parent_spaces)


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


@app.route('/about/', defaults={'path': 'index'})
@app.route('/about/policy/', defaults={'path': 'policy/index'})
@app.route('/about/<path:path>')
def about(path):
    return render_template('about.html.jinja2', page=pages.get_or_404(os.path.join('about', path)))
