"""Home page and static pages."""

from __future__ import annotations

from dataclasses import dataclass
import os.path

from flask import Response, g, render_template

from baseframe import _, __
from baseframe.filters import date_filter
from coaster.views import ClassView, render_with, requestargs, route

from .. import app, pages
from ..forms import SavedProjectForm
from ..models import Project, db
from ..typing import ReturnRenderWith, ReturnView


@dataclass
class PolicyPage:
    """Policy page."""

    path: str
    title: str


policy_pages = [
    PolicyPage('policy/terms', __("Terms of service")),
    PolicyPage('policy/adtos', __("Sponsorship &amp; advertising")),
    PolicyPage('policy/privacy', __("Privacy policy")),
    PolicyPage('policy/refunds', __("Cancellation &amp; refund policy")),
    PolicyPage('policy/community', __("Community guidelines")),
    PolicyPage('policy/code', __("Code of conduct")),
]


@route('/')
class IndexView(ClassView):
    current_section = 'home'
    SavedProjectForm = SavedProjectForm

    @route('', endpoint='index')
    @render_with('index.html.jinja2')
    def home(self) -> ReturnRenderWith:
        g.profile = None
        projects = Project.all_unsorted()
        # TODO: Move these queries into the Project class
        all_projects = (
            projects.filter(
                Project.state.PUBLISHED,
                db.or_(
                    Project.state.LIVE,
                    Project.state.UPCOMING,
                    db.and_(
                        Project.start_at.is_(None),
                        Project.published_at.isnot(None),
                        Project.site_featured.is_(True),
                    ),
                ),
            )
            .order_by(Project.next_session_at.asc())
            .all()
        )
        upcoming_projects = all_projects[:3]
        all_projects = all_projects[3:]
        featured_project = (
            projects.filter(
                Project.state.PUBLISHED,
                db.or_(
                    Project.state.LIVE,
                    Project.state.UPCOMING,
                    db.and_(
                        Project.start_at.is_(None), Project.published_at.isnot(None)
                    ),
                ),
                Project.site_featured.is_(True),
            )
            .order_by(Project.next_session_at.asc())
            .limit(1)
            .first()
        )
        if featured_project in upcoming_projects:
            # if featured project is in upcoming projects, remove it from there and
            # pick one upcoming project from from all projects, only if
            # there are any projects left in it
            upcoming_projects.remove(featured_project)
            if all_projects:
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


IndexView.init_app(app)


@app.route('/past.json')
@requestargs(('page', int), ('per_page', int))
def past_projects_json(page: int = 1, per_page: int = 10) -> ReturnView:
    g.profile = None
    projects = Project.all_unsorted()
    past_projects = projects.filter(Project.state.PAST).order_by(
        Project.start_at.desc()
    )
    pagination = past_projects.paginate(page=page, per_page=per_page)
    return {
        'status': 'ok',
        'title': _('Past sessions'),
        'headings': [_('Date'), _('Project'), _('Location')],
        'next_page': pagination.page + 1 if pagination.page < pagination.pages else '',
        'total_pages': pagination.pages,
        'past_projects': [
            {
                'title': p.title,
                'datetime': date_filter(p.end_at_localized, format='dd MMM yyyy'),
                'venue': p.primary_venue.city if p.primary_venue else p.location,
                'url': p.url_for(),
            }
            for p in pagination.items
        ],
    }


@app.route('/about')
def about() -> ReturnView:
    return render_template('about.html.jinja2')


@app.route('/about/contact')
def contact() -> ReturnView:
    return render_template(
        'contact.html.jinja2', page=pages.get_or_404('about/contact')
    )


# Trailing slash in `/about/policy/` is required for relative links in `index.md`
@app.route('/about/policy/', defaults={'path': 'policy/index'})
@app.route('/about/<path:path>')
def policy(path: str) -> ReturnView:
    return render_template(
        'policy.html.jinja2',
        index=policy_pages,
        page=pages.get_or_404(os.path.join('about', path)),
    )


@app.route('/opensearch.xml')
def opensearch() -> ReturnView:
    return Response(
        render_template('opensearch.xml.jinja2'),
        mimetype='application/opensearchdescription+xml',
    )


@app.route('/robots.txt')
def robotstxt() -> ReturnView:
    return Response(render_template('robots.txt.jinja2'), mimetype='text/plain')
