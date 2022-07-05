"""Views for a user or organization profile."""

from __future__ import annotations

from flask import abort, current_app, flash, render_template, request

from baseframe import _
from baseframe.filters import date_filter
from baseframe.forms import render_form
from coaster.auth import current_auth
from coaster.views import (
    ModelView,
    UrlChangeCheck,
    UrlForView,
    get_next_url,
    render_with,
    requestargs,
    requires_roles,
    route,
)

from .. import app
from ..forms import (
    ProfileBannerForm,
    ProfileForm,
    ProfileLogoForm,
    ProfileTransitionForm,
)
from ..models import Profile, Project, db
from .helpers import render_redirect
from .login_session import requires_login, requires_user_not_spammy
from .mixins import ProfileViewMixin


@Profile.features('new_project')
def feature_profile_new_project(obj):
    return (
        obj.is_organization_profile
        and obj.current_roles.admin
        and bool(obj.state.PUBLIC)
    )


@Profile.features('new_user_project')
def feature_profile_new_user_project(obj):
    return (
        obj.is_user_profile
        and obj.current_roles.admin
        and obj.is_active
        and bool(obj.state.PUBLIC)
    )


@Profile.features('make_public')
def feature_profile_make_public(obj):
    return obj.current_roles.admin and obj.make_public.is_available


@Profile.features('make_private')
def feature_profile_make_private(obj):
    return obj.current_roles.admin and obj.make_private.is_available


def template_switcher(templateargs):
    template = templateargs.pop('template')
    return render_template(template, **templateargs)


@Profile.views('main')
@route('/<profile>')
class ProfileView(ProfileViewMixin, UrlChangeCheck, UrlForView, ModelView):
    @route('')
    @render_with({'text/html': template_switcher}, json=True)
    @requires_roles({'reader', 'admin'})
    def view(self):
        template_name = None
        ctx = {}

        if self.obj.is_user_profile:
            template_name = 'user_profile.html.jinja2'

            submitted_proposals = self.obj.user.public_proposals

            tagged_sessions = [
                proposal.session
                for proposal in submitted_proposals
                if proposal.session is not None
            ]

            ctx = {
                'template': template_name,
                'profile': self.obj.current_access(datasets=('primary', 'related')),
                'tagged_sessions': [
                    session.current_access() for session in tagged_sessions
                ],
            }

        elif self.obj.is_organization_profile:
            template_name = 'profile.html.jinja2'

            # `order_by(None)` clears any existing order defined in relationship.
            # We're using it because we want to define our own order here.
            # listed_projects already includes a filter on Project.state.PUBLISHED
            projects = self.obj.listed_projects.order_by(None)
            all_projects = (
                projects.filter(
                    db.or_(
                        Project.state.LIVE,
                        Project.state.UPCOMING,
                        db.and_(
                            Project.start_at.is_(None), Project.published_at.isnot(None)
                        ),
                    ),
                )
                .order_by(Project.order_by_date())
                .all()
            )

            upcoming_projects = all_projects[:3]
            all_projects = all_projects[3:]
            featured_project = (
                projects.filter(
                    db.or_(
                        Project.state.LIVE,
                        Project.state.UPCOMING,
                        db.and_(
                            Project.start_at.is_(None), Project.published_at.isnot(None)
                        ),
                    ),
                    Project.site_featured.is_(True),
                )
                .order_by(Project.order_by_date())
                .limit(1)
                .first()
            )
            if featured_project in upcoming_projects:
                upcoming_projects.remove(featured_project)
            open_cfp_projects = (
                projects.filter(Project.cfp_state.OPEN)
                .order_by(Project.order_by_date())
                .all()
            )

            # If the user is an admin of this profile, show all draft projects.
            # Else, only show the drafts they have a crew role in
            if self.obj.current_roles.admin:
                draft_projects = self.obj.draft_projects
                unscheduled_projects = self.obj.projects.filter(
                    Project.state.PUBLISHED_WITHOUT_SESSIONS
                ).all()
            else:
                draft_projects = self.obj.draft_projects_for(current_auth.user)
                unscheduled_projects = self.obj.unscheduled_projects_for(
                    current_auth.user
                )

            sponsored_projects = self.obj.sponsored_projects
            sponsored_submissions = self.obj.sponsored_proposals

            ctx = {
                'template': template_name,
                'profile': self.obj.current_access(datasets=('primary', 'related')),
                'all_projects': [
                    p.current_access(datasets=('without_parent', 'related'))
                    for p in all_projects
                ],
                'unscheduled_projects': [
                    p.current_access(datasets=('without_parent', 'related'))
                    for p in unscheduled_projects
                ],
                'upcoming_projects': [
                    p.current_access(datasets=('without_parent', 'related'))
                    for p in upcoming_projects
                ],
                'open_cfp_projects': [
                    p.current_access(datasets=('without_parent', 'related'))
                    for p in open_cfp_projects
                ],
                'draft_projects': [
                    p.current_access(datasets=('without_parent', 'related'))
                    for p in draft_projects
                ],
                'featured_project': (
                    featured_project.current_access(
                        datasets=('without_parent', 'related')
                    )
                    if featured_project
                    else None
                ),
                'sponsored_projects': [
                    _p.current_access(datasets=('primary', 'related'))
                    for _p in sponsored_projects
                ],
                'sponsored_submissions': [
                    _p.current_access(datasets=('primary', 'related'))
                    for _p in sponsored_submissions
                ],
            }
        else:
            abort(404)  # Reserved profile

        return ctx

    @route('in/projects')
    @render_with('user_profile_projects.html.jinja2', json=True)
    @requires_roles({'reader', 'admin'})
    def user_participated_projects(self):
        if self.obj.is_organization_profile:
            abort(404)

        participated_projects = set(self.obj.user.projects_as_crew) | {
            _p.project for _p in self.obj.user.public_proposals
        }

        return {
            'profile': self.obj.current_access(datasets=('primary', 'related')),
            'participated_projects': [
                project.current_access(datasets=('without_parent', 'related'))
                for project in participated_projects
            ],
        }

    @route('in/submissions')
    @route('in/proposals')  # Legacy route, will be auto-redirected to `in/submissions`
    @render_with('user_profile_proposals.html.jinja2', json=True)
    @requires_roles({'reader', 'admin'})
    def user_proposals(self):
        if self.obj.is_organization_profile:
            abort(404)

        submitted_proposals = self.obj.user.public_proposals

        return {
            'profile': self.obj.current_access(datasets=('primary', 'related')),
            'submitted_proposals': [
                proposal.current_access(datasets=('without_parent', 'related'))
                for proposal in submitted_proposals
            ],
        }

    @route('past.json')
    @requestargs(('page', int), ('per_page', int))
    def past_projects_json(self, page=1, per_page=10):
        projects = self.obj.listed_projects.order_by(None)
        past_projects = projects.filter(Project.state.PAST).order_by(
            Project.start_at.desc()
        )
        pagination = past_projects.paginate(page=page, per_page=per_page)
        return {
            'status': 'ok',
            'title': _('Past sessions'),
            'headings': [_('Date'), _('Project'), _('Location')],
            'next_page': (
                pagination.page + 1 if pagination.page < pagination.pages else ''
            ),
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

    @route('edit', methods=['GET', 'POST'])
    @requires_roles({'admin'})
    @requires_user_not_spammy()
    def edit(self):
        form = ProfileForm(
            obj=self.obj, model=Profile, profile=self.obj, user=current_auth.user
        )
        if self.obj.user:
            form.make_for_user()
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return render_redirect(self.obj.url_for())
        return render_form(
            form=form,
            title=_("Edit profile details"),
            submit=_("Save changes"),
            cancel_url=self.obj.url_for(),
            ajax=False,
        )

    @route('update_logo', methods=['GET', 'POST'])
    @render_with('update_logo_modal.html.jinja2')
    @requires_roles({'admin'})
    def update_logo(self):
        form = ProfileLogoForm(profile=self.obj)
        edit_logo_url = self.obj.url_for('edit_logo_url')
        delete_logo_url = self.obj.url_for('remove_logo')
        return {
            'edit_logo_url': edit_logo_url,
            'delete_logo_url': delete_logo_url,
            'form': form,
        }

    @route('edit_logo', methods=['GET', 'POST'])
    @requires_roles({'admin'})
    @requires_user_not_spammy()
    def edit_logo_url(self):
        form = ProfileLogoForm(obj=self.obj, profile=self.obj)
        if request.method == 'POST':
            if form.validate_on_submit():
                form.populate_obj(self.obj)
                db.session.commit()
                flash(_("Your changes have been saved"), 'info')
                return render_redirect(self.obj.url_for())
            return render_form(form=form, title="", submit=_("Save logo"), ajax=True)
        return render_form(
            form=form,
            title="",
            submit=_("Save logo"),
            ajax=True,
            template='img_upload_formlayout.html.jinja2',
        )

    @route('remove_logo', methods=['POST'])
    @requires_login
    @requires_roles({'admin'})
    def remove_logo(self):
        form = self.CsrfForm()
        if form.validate_on_submit():
            self.obj.logo_url = None
            db.session.commit()
            return render_redirect(self.obj.url_for())
        current_app.logger.error(
            "CSRF form validation error when removing profile logo"
        )
        flash(_("Were you trying to remove the logo? Try again to confirm"), 'error')
        return render_redirect(self.obj.url_for())

    @route('update_banner', methods=['GET', 'POST'])
    @render_with('update_logo_modal.html.jinja2')
    @requires_roles({'admin'})
    def update_banner(self):
        form = ProfileBannerForm(profile=self.obj)
        edit_logo_url = self.obj.url_for('edit_banner_image_url')
        delete_logo_url = self.obj.url_for('remove_banner')
        return {
            'edit_logo_url': edit_logo_url,
            'delete_logo_url': delete_logo_url,
            'form': form,
        }

    @route('edit_banner', methods=['GET', 'POST'])
    @requires_roles({'admin'})
    def edit_banner_image_url(self):
        form = ProfileBannerForm(obj=self.obj, profile=self.obj)
        if request.method == 'POST':
            if form.validate_on_submit():
                form.populate_obj(self.obj)
                db.session.commit()
                flash(_("Your changes have been saved"), 'info')
                return render_redirect(self.obj.url_for())
            return render_form(form=form, title="", submit=_("Save banner"), ajax=True)
        return render_form(
            form=form,
            title="",
            submit=_("Save banner"),
            ajax=True,
            template='img_upload_formlayout.html.jinja2',
        )

    @route('remove_banner', methods=['POST'])
    @requires_login
    @requires_roles({'admin'})
    def remove_banner(self):
        form = self.CsrfForm()
        if form.validate_on_submit():
            self.obj.banner_image_url = None
            db.session.commit()
            return render_redirect(self.obj.url_for())
        current_app.logger.error(
            "CSRF form validation error when removing profile banner"
        )
        flash(
            _("Were you trying to remove the banner? Try again to confirm"),
            'error',
        )
        return render_redirect(self.obj.url_for())

    @route('transition', methods=['POST'])
    @requires_login
    @requires_roles({'owner'})
    def transition(self):
        form = ProfileTransitionForm(obj=self.obj)
        if form.validate_on_submit():
            transition_name = form.transition.data
            getattr(self.obj, transition_name)()
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
        else:
            flash(
                _("There was a problem saving your changes. Please try again"), 'error'
            )
        return render_redirect(get_next_url(referrer=True))


ProfileView.init_app(app)
