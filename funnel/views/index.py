# -*- coding: utf-8 -*-

import os.path
from flask import g, render_template, redirect, jsonify, Response, url_for
from coaster.views import jsonp, load_model, render_with
from .. import app, funnelapp, pages, lastuser
from ..models import Project, Proposal
from .project import project_data


def index_jsonify(data):
    return jsonify(projects=[d for d in [s.current_access() for s in data['projects']] if d])


@app.route('/')
@render_with({'text/html': 'index.html.jinja2', 'application/json': index_jsonify})
def index():
    g.profile = None
    projects = Project.all_unsorted(legacy=False)  # NOQA
    all_projects = projects.filter(Project.state.UPCOMING).order_by(Project.date.asc()).all()
    upcoming_projects = all_projects[:3]
    all_projects = all_projects[3:]
    featured_project = projects.filter(Project.state.UPCOMING).filter(Project.featured == True) \
        .order_by(Project.date.asc()).limit(1).first()  # NOQA
    upcoming_projects.remove(featured_project)
    open_cfp_projects = projects.filter(Project.cfp_state.OPEN).order_by(Project.date.asc()).all()
    return {'projects': projects.all(), 'all_projects': all_projects,
        'upcoming_projects': upcoming_projects, 'open_cfp_projects': open_cfp_projects,
        'featured_project': featured_project}


@funnelapp.route('/', endpoint='index')
@render_with({'text/html': 'funnelindex.html.jinja2', 'application/json': index_jsonify})
def talkfunnel_index():
    g.profile = None
    projects = Project.fetch_sorted(legacy=True).all()  # NOQA
    return {'projects': projects}


@app.route('/account')
@lastuser.requires_login
def account():
    return render_template('account.html.jinja2')


@funnelapp.route('/account', endpoint='account')
def talkfunnel_account():
    with app.app_context(), app.test_request_context():
        return redirect(url_for('account', _external=True))


@app.route('/api/whoami')
@funnelapp.route('/api/whoami')
def whoami():
    if g.user:
        return jsonify(message="Hey {0}!".format(g.user.fullname), code=200)
    else:
        return jsonify(message="Hmm, so who _are_ you?", code=401)


@app.route('/json')
def all_projects_json():
    g.profile = None
    projects = Project.fetch_sorted(legacy=False).all()  # NOQA
    return jsonp(projects=map(project_data, projects),
        spaces=map(project_data, projects))  # FIXME: Remove when the native app switches over


@funnelapp.route('/json')
def funnelapp_all_projects_json():
    g.profile = None
    projects = Project.fetch_sorted().all()  # NOQA
    return jsonp(projects=map(project_data, projects),
        spaces=map(project_data, projects))  # FIXME: Remove when the native app switches over


@funnelapp.route('/<project>/<int:id>-<name>')
@funnelapp.route('/<project>/<int:id>')
@load_model(Proposal, {'id': 'id'}, 'proposal')
def proposal_redirect(proposal):
    return redirect(proposal.url_for())


@app.route('/about/', defaults={'path': 'index'})
@app.route('/about/policy/', defaults={'path': 'policy/index'})
@app.route('/about/<path:path>')
def about(path):
    return render_template('about.html.jinja2', page=pages.get_or_404(os.path.join('about', path)))


@app.route('/api/1/template/offline')
def offline():
    return render_template('offline.html.jinja2')


@app.route('/service-worker.js', methods=['GET'])
def sw():
    return app.send_static_file('service-worker.js')


@app.route('/manifest.json', methods=['GET'])
def manifest():
    return Response(render_template('manifest.json.jinja2'), mimetype='application/json')
