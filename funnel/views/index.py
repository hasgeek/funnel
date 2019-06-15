# -*- coding: utf-8 -*-

import os.path
from flask import g, render_template, redirect, jsonify, Response
from coaster.views import jsonp, load_model, render_with, ClassView, route
from .. import app, funnelapp, pages
from ..models import Project, Proposal
from .project import project_data


def index_jsonify(data):
    return jsonify(projects=[d for d in [s.current_access() for s in data['projects']] if d])


@route('/')
class IndexView(ClassView):
    @render_with({'text/html': 'index.html.jinja2', 'application/json': index_jsonify})
    def home(self):
        g.profile = None
        projects = Project.all_unsorted(legacy=False)  # NOQA
        all_projects = projects.filter(Project.state.UPCOMING).order_by(Project.schedule_start_at.asc()).all()
        upcoming_projects = all_projects[:3]
        all_projects = all_projects[3:]
        featured_project = projects.filter(Project.state.UPCOMING).filter(Project.featured == True) \
            .order_by(Project.schedule_start_at.asc()).limit(1).first()  # NOQA
        if featured_project in upcoming_projects:
            upcoming_projects.remove(featured_project)
        open_cfp_projects = projects.filter(Project.cfp_state.OPEN).order_by(Project.schedule_start_at.asc()).all()
        return {'projects': projects.all(), 'all_projects': all_projects,
            'upcoming_projects': upcoming_projects, 'open_cfp_projects': open_cfp_projects,
            'featured_project': featured_project}


@route('/')
class FunnelIndexView(ClassView):
    @render_with({'text/html': 'funnelindex.html.jinja2', 'application/json': index_jsonify})
    def home(self):
        g.profile = None
        projects = Project.fetch_sorted(legacy=True).all()  # NOQA
        return {'projects': projects}


IndexView.add_route_for('home', '', endpoint='index')
IndexView.init_app(app)
FunnelIndexView.add_route_for('home', '', endpoint='index')
FunnelIndexView.init_app(funnelapp)


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
