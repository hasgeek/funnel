import os.path

from flask import Response, g, jsonify, redirect, render_template, url_for

from baseframe import _
from baseframe.filters import date_filter
from coaster.auth import current_auth
from coaster.views import ClassView, jsonp, load_model, render_with, requestargs, route

from .. import app, funnelapp, lastuserapp, pages
from ..forms import SavedProjectForm
from ..models import Project, Proposal, db
from .helpers import app_url_for
from .project import project_data


@route('/')
class IndexView(ClassView):
    current_section = 'home'
    SavedProjectForm = SavedProjectForm

    @render_with('index.html.jinja2')
    def home(self):
        g.profile = None
        projects = Project.all_unsorted(legacy=False)
        # TODO: Move these queries into the Project class
        all_projects = (
            projects.filter(
                Project.state.PUBLISHED,
                db.or_(Project.schedule_state.LIVE, Project.schedule_state.UPCOMING),
            )
            .order_by(Project.next_session_at.asc())
            .all()
        )
        upcoming_projects = all_projects[:3]
        all_projects = all_projects[3:]
        featured_project = (
            projects.filter(
                Project.state.PUBLISHED,
                db.or_(Project.schedule_state.LIVE, Project.schedule_state.UPCOMING),
                Project.featured.is_(True),
            )
            .order_by(Project.next_session_at.asc())
            .limit(1)
            .first()
        )
        if featured_project in upcoming_projects:
            upcoming_projects.remove(featured_project)
            upcoming_projects.append(all_projects.pop(0))
        open_cfp_projects = (
            projects.filter(Project.state.PUBLISHED, Project.cfp_state.OPEN)
            .order_by(Project.next_session_at.asc())
            .all()
        )

        return {
            'all_projects': [
                p.access_for(roles={'all'}, datasets=('primary', 'related'))
                for p in all_projects
            ],
            'upcoming_projects': [
                p.access_for(roles={'all'}, datasets=('primary', 'related'))
                for p in upcoming_projects
            ],
            'open_cfp_projects': [
                p.access_for(roles={'all'}, datasets=('primary', 'related'))
                for p in open_cfp_projects
            ],
            'featured_project': (
                featured_project.access_for(
                    roles={'all'}, datasets=('primary', 'related')
                )
                if featured_project
                else None
            ),
        }


@route('/')
class FunnelIndexView(ClassView):
    @render_with('funnelindex.html.jinja2')
    def home(self):
        g.profile = None
        projects = Project.fetch_sorted(legacy=True).all()
        return {'projects': projects}


IndexView.add_route_for('home', '', endpoint='index')
IndexView.init_app(app)
FunnelIndexView.add_route_for('home', '', endpoint='index')
FunnelIndexView.init_app(funnelapp)


@app.route('/api/whoami')
@funnelapp.route('/api/whoami')
def whoami():
    if current_auth.user:
        return jsonify(message="Hey {0}!".format(current_auth.user.fullname), code=200)
    else:
        return jsonify(message="Hmm, so who _are_ you?", code=401)


@app.route('/past.json')
@requestargs(('page', int), ('per_page', int))
def past_projects_json(page=1, per_page=10):
    g.profile = None
    projects = Project.all_unsorted(legacy=False)
    past_projects = projects.filter(
        Project.state.PUBLISHED, Project.schedule_state.PAST
    ).order_by(Project.schedule_start_at.desc())
    pagination = past_projects.paginate(page=page, per_page=per_page)
    return {
        'status': 'ok',
        'title': 'Past projects',
        'headings': ['Date', 'Project', 'Location'],
        'next_page': pagination.page + 1 if pagination.page < pagination.pages else '',
        'total_pages': pagination.pages,
        'past_projects': [
            {
                'title': p.title,
                'datetime': date_filter(
                    p.schedule_start_at_localized, format='dd MMM yyyy'
                ),
                'venue': p.primary_venue.city if p.primary_venue else p.location,
                'url': p.url_for(),
            }
            for p in pagination.items
        ],
    }


@funnelapp.route('/json')
def funnelapp_all_projects_json():
    g.profile = None
    projects = Project.fetch_sorted().all()
    return jsonp(
        projects=list(map(project_data, projects)),
        spaces=list(map(project_data, projects)),
    )  # FIXME: Remove when the native app switches over


@funnelapp.route('/<project>/<int:id>-<name>')
@funnelapp.route('/<project>/<int:id>')
@load_model(Proposal, {'id': 'id'}, 'proposal')
def proposal_redirect(proposal):
    return redirect(proposal.url_for())


@app.route('/about')
def about():
    return render_template('about.html.jinja2')


@app.route('/about/contact', defaults={'path': 'contact'})
def contact(path):
    return render_template(
        'contact.html.jinja2',
        path=path,
        page=pages.get_or_404(os.path.join('about', path)),
    )


@app.route('/about/policy', defaults={'path': 'policy/index'})
@app.route('/about/<path:path>')
def policy(path):
    return render_template(
        'policy.html.jinja2', page=pages.get_or_404(os.path.join('about', path))
    )


@app.route('/api/1/template/offline')
def offline():
    return render_template('offline.html.jinja2')


@app.route('/service-worker.js')
def sw():
    return app.send_static_file('service-worker.js')


@app.route('/manifest.json')
@app.route('/manifest.webmanifest')
def manifest():
    return jsonify(
        {
            "name": app.config['SITE_TITLE'],
            "short_name": app.config['SITE_TITLE'],
            "description": _("Discussion spaces for geeks"),
            "scope": "/",
            "theme_color": "#e3e1e1",
            "background_color": "#ffffff",
            "display": "standalone",
            "orientation": "portrait",
            "start_url": "/?utm_source=WebApp",
            "icons": [
                {
                    "src": url_for(
                        'static', filename='img/android-chrome-192x192.png', v=2
                    ),
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "any",
                },
                {
                    "src": url_for(
                        'static', filename='img/android-chrome-512x512.png', v=2
                    ),
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any",
                },
            ],
        }
    )


@app.route('/opensearch.xml')
def opensearch():
    return Response(
        render_template('opensearch.xml.jinja2'),
        mimetype='application/opensearchdescription+xml',
    )


# --- Lastuser legacy routes -----------------------------------------------------------


@lastuserapp.route('/', endpoint='index')
def lastuser_index():
    return redirect(app_url_for(app, 'index'))
