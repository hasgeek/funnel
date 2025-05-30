"""Home page and static pages."""

from __future__ import annotations

import os.path
from dataclasses import dataclass

from flask import Response, g, render_template
from flask_flatpages import Page
from markupsafe import Markup

from baseframe import _, __
from baseframe.filters import date_filter
from baseframe.forms import render_message
from coaster.sqlalchemy import RoleAccessProxy
from coaster.views import ClassView, render_with, requestargs, route

from .. import app, pages
from ..forms import SavedProjectForm
from ..models import Account, Project, Venue, sa
from ..typing import ReturnRenderWith, ReturnView
from .helpers import LayoutTemplate
from .schedule import schedule_data, session_list_data


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
    PolicyPage('policy/posh', __("POSH policy")),
]


class AboutTemplate(LayoutTemplate, template='about.html.jinja2'):
    pass


class ContactTemplate(LayoutTemplate, template='contact.html.jinja2'):
    page: Page


class PolicyTemplate(LayoutTemplate, template='policy.html.jinja2'):
    index: list[PolicyPage]
    page: Page


class IndexTemplate(LayoutTemplate, template='index.html.jinja2'):
    upcoming_projects: list[Project | RoleAccessProxy[Project]]
    open_cfp_projects: list[Project | RoleAccessProxy[Project]]
    featured_project: Project | RoleAccessProxy[Project] | None
    featured_project_venues: list[Venue] | list[RoleAccessProxy[Venue]] | None
    featured_project_sessions: list[dict] | None  # TODO: Specify precise type
    featured_project_schedule: list[dict] | None  # TODO: Specify precise type
    featured_accounts: list[Account | RoleAccessProxy[Account]]


@route('/', init_app=app)
class IndexView(ClassView):
    current_section = 'home'
    SavedProjectForm = SavedProjectForm

    @route('', endpoint='index')
    def home(self) -> ReturnView:
        g.account = None
        projects = Project.all_unsorted()
        # TODO: Move these queries into the Project class
        upcoming_projects = (
            projects.filter(
                Project.state.PUBLISHED,
                sa.or_(
                    Project.state.LIVE,
                    Project.state.UPCOMING,
                    sa.and_(
                        Project.start_at.is_(None),
                        Project.published_at.is_not(None),
                        Project.site_featured.is_(True),
                    ),
                ),
            )
            .order_by(Project.next_session_at.asc())
            .all()
        )
        featured_project = (
            projects.filter(
                Project.state.PUBLISHED,
                sa.or_(
                    Project.state.LIVE,
                    Project.state.UPCOMING,
                    sa.and_(
                        Project.start_at.is_(None), Project.published_at.is_not(None)
                    ),
                ),
                Project.site_featured.is_(True),
            )
            .order_by(Project.next_session_at.asc())
            .limit(1)
            .first()
        )
        scheduled_sessions_list = (
            session_list_data(
                featured_project.scheduled_sessions, with_modal_url='view'
            )
            if featured_project
            else None
        )
        featured_project_venues = (
            [
                venue.current_access(datasets=('without_parent', 'related'))
                for venue in featured_project.venues
            ]
            if featured_project
            else None
        )
        featured_project_schedule = (
            schedule_data(
                featured_project,
                with_slots=False,
                scheduled_sessions=scheduled_sessions_list,
            )
            if featured_project
            else None
        )
        if featured_project in upcoming_projects:
            # if featured project is in upcoming projects, remove it from there and
            # pick one upcoming project from from all projects, only if
            # there are any projects left in it
            upcoming_projects.remove(featured_project)
        open_cfp_projects = (
            projects.filter(Project.state.PUBLISHED, Project.cfp_state.OPEN)
            .order_by(Project.next_session_at.asc())
            .all()
        )
        # Get featured accounts
        featured_accounts = Account.query.filter(
            Account.name_in(app.config['FEATURED_ACCOUNTS'])
        ).all()
        # This list will not be ordered, so we have to re-sort
        featured_account_sort_key = {
            _n.lower(): _i for _i, _n in enumerate(app.config['FEATURED_ACCOUNTS'])
        }
        featured_accounts.sort(
            key=lambda a: featured_account_sort_key[(a.name or a.title).lower()]
        )

        return IndexTemplate(
            upcoming_projects=[p.current_access() for p in upcoming_projects],
            open_cfp_projects=[p.current_access() for p in open_cfp_projects],
            featured_project=(
                featured_project.current_access() if featured_project else None
            ),
            featured_project_venues=featured_project_venues,
            featured_project_sessions=scheduled_sessions_list,
            featured_project_schedule=featured_project_schedule,
            featured_accounts=[p.current_access() for p in featured_accounts],
        ).render_template()

    @route('past.projects', endpoint='past_projects')
    @render_with('past_projects_section.html.jinja2')
    @requestargs(('page', int), ('per_page', int))
    def past_projects(self, page: int = 1, per_page: int = 10) -> ReturnRenderWith:
        g.account = None
        projects = Project.all_unsorted()
        pagination = (
            projects.filter(Project.state.PAST)
            .order_by(Project.end_at.desc())
            .paginate(page=page, per_page=per_page)
        )
        return {
            'status': 'ok',
            'next_page': (
                pagination.page + 1 if pagination.page < pagination.pages else ''
            ),
            'total_pages': pagination.pages,
            'past_projects': [
                {
                    'title': p.title,
                    'datetime': date_filter(
                        p.end_at_localized,  # type: ignore[arg-type]
                        format='dd MMM yyyy',
                    ),
                    'venue': p.primary_venue.city if p.primary_venue else p.location,
                    'url': p.url_for(),
                }
                for p in pagination.items
            ],
        }


@app.route('/about')
def about() -> ReturnView:
    return AboutTemplate().render_template()


@app.route('/about/contact')
def contact() -> ReturnView:
    return ContactTemplate(page=pages.get_or_404('about/contact')).render_template()


# Trailing slash in `/about/policy/` is required for relative links in `index.md`
@app.route('/about/policy/', defaults={'path': 'policy/index'})
@app.route('/about/<path:path>')
def policy(path: str) -> ReturnView:
    return PolicyTemplate(
        index=policy_pages,
        page=pages.get_or_404(os.path.join('about', path)),
    ).render_template()


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
                " will not gain access to your account without the OTP.<br/><br/>"
                "However, if you suspect misbehaviour of any form, please report it"
                " to us. Email:"
                ' <a href="mailto:{email}">{email}</a>, phone:'
                ' <a href="tel:{phone}">{phone_formatted}</a>.'
            )
        ).format(
            email=app.config['SITE_SUPPORT_EMAIL'],
            phone=app.config['SITE_SUPPORT_PHONE'],
            phone_formatted=app.config['SITE_SUPPORT_PHONE_FORMATTED'],
        ),
    )
