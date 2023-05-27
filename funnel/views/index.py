"""Home page and static pages."""

from __future__ import annotations

from dataclasses import dataclass
import os.path

from flask import Response, g, render_template
from markupsafe import Markup

from baseframe import _, __
from baseframe.filters import date_filter
from baseframe.forms import render_message
from coaster.views import ClassView, render_with, requestargs, route

from .. import app, pages
from ..forms import SavedProjectForm
from ..models import Profile, Project, sa
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
                sa.or_(
                    Project.state.LIVE,
                    Project.state.UPCOMING,
                    sa.and_(
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
                sa.or_(
                    Project.state.LIVE,
                    Project.state.UPCOMING,
                    sa.and_(
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
            'featured_profiles': [
                p.current_access(datasets=('primary', 'related'))
                for p in Profile.query.filter(
                    Profile.is_verified.is_(True),
                    Profile.organization_id.isnot(None),
                )
                .order_by(sa.func.random())
                .limit(6)
            ],
        }


IndexView.init_app(app)


@app.route('/past.projects', endpoint='past_projects')
@requestargs(('page', int), ('per_page', int))
@render_with('past_projects_section.html.jinja2')
def past_projects(page: int = 1, per_page: int = 10) -> ReturnView:
    g.profile = None
    projects = Project.all_unsorted()
    pagination = (
        projects.filter(Project.state.PAST)
        .order_by(Project.start_at.desc())
        .paginate(page=page, per_page=per_page)
    )
    return {
        'status': 'ok',
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


@app.route('/account/not-my-otp')
def not_my_otp() -> ReturnView:
    """Show help page for OTP misuse."""
    return render_message(
        title=_("Did not request an OTP?"),
        message=Markup(
            _(
                "If you’ve received an OTP without requesting it, someone may have made"
                " a typo in their own phone number and accidentally used yours. They"
                " will not gain access to your account without the OTP.<br><br>"
                "However, if you suspect misbehaviour of any form, please report it"
                " to us. Email:"
                ' <a href="mailto:support@hasgeek.com">support@hasgeek.com</a>, phone:'
                ' <a href="tel:+917676332020">+91 7676 33 2020</a>.'
            )
        ),
    )
