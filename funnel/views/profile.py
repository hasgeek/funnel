from flask import Response, abort, flash, redirect, render_template, request

from baseframe import _
from baseframe.filters import date_filter
from baseframe.forms import render_form, render_redirect
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

from .. import app, funnelapp
from ..forms import ProfileBannerForm, ProfileForm, ProfileLogoForm
from ..models import Profile, Project, Proposal, db
from .decorators import legacy_redirect
from .login_session import requires_login
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
    return obj.is_user_profile and obj.current_roles.admin and bool(obj.state.PUBLIC)


@Profile.features('make_public')
def feature_profile_make_public(obj):
    return obj.current_roles.admin and not bool(obj.state.PUBLIC)


@Profile.features('make_private')
def feature_profile_make_private(obj):
    return obj.current_roles.admin and bool(obj.state.PUBLIC)


def template_switcher(templateargs):
    template = templateargs.pop('template')
    return Response(render_template(template, **templateargs), mimetype='text/html')


@Profile.views('main')
@route('/<profile>')
class ProfileView(ProfileViewMixin, UrlChangeCheck, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('')
    @render_with({'*/*': template_switcher}, json=True)
    @requires_roles({'reader', 'admin'})
    def view(self):
        template_name = None
        ctx = {}

        if self.obj.is_user_profile:
            template_name = 'user_profile.html.jinja2'

            submitted_proposals = self.obj.user.speaker_at.filter(
                ~(Proposal.state.DRAFT), ~(Proposal.state.DELETED)
            ).all()

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
            projects = self.obj.listed_projects.order_by(None)
            all_projects = (
                projects.filter(
                    Project.state.PUBLISHED,
                    db.or_(
                        Project.schedule_state.LIVE, Project.schedule_state.UPCOMING
                    ),
                )
                .order_by(Project.schedule_start_at.asc())
                .all()
            )
            upcoming_projects = all_projects[:3]
            all_projects = all_projects[3:]
            featured_project = (
                projects.filter(
                    Project.state.PUBLISHED,
                    db.or_(
                        Project.schedule_state.LIVE, Project.schedule_state.UPCOMING
                    ),
                    Project.featured.is_(True),
                )
                .order_by(Project.schedule_start_at.asc())
                .limit(1)
                .first()
            )
            if featured_project in upcoming_projects:
                upcoming_projects.remove(featured_project)
            open_cfp_projects = (
                projects.filter(Project.state.PUBLISHED, Project.cfp_state.OPEN)
                .order_by(Project.schedule_start_at.asc())
                .all()
            )

            # If the user is an admin of this profile, show all draft projects.
            # Else, only show the drafts they have a crew role in
            if self.obj.current_roles.admin:
                draft_projects = self.obj.draft_projects
                unscheduled_projects = self.obj.projects.filter(
                    Project.schedule_state.PUBLISHED_WITHOUT_SESSIONS
                ).all()
            else:
                draft_projects = self.obj.draft_projects_for(current_auth.user)
                unscheduled_projects = self.obj.unscheduled_projects_for(
                    current_auth.user
                )

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

        submitted_proposals = self.obj.user.speaker_at.filter(
            ~(Proposal.state.DRAFT), ~(Proposal.state.DELETED)
        ).all()

        participated_project_ids = [
            proposal.project_id for proposal in submitted_proposals
        ] + [project.id for project in self.obj.user.projects_as_crew]

        participated_projects = Project.query.filter(
            Project.state.PUBLISHED,
            Project.schedule_start_at.isnot(None),
            Project.id.in_(set(participated_project_ids)),
        ).order_by(Project.schedule_start_at.desc())

        return {
            'profile': self.obj.current_access(datasets=('primary', 'related')),
            'participated_projects': [
                project.current_access(datasets=('without_parent', 'related'))
                for project in participated_projects
            ],
        }

    @route('in/proposals')
    @render_with('user_profile_proposals.html.jinja2', json=True)
    @requires_roles({'reader', 'admin'})
    def user_proposals(self):
        if self.obj.is_organization_profile:
            abort(404)

        submitted_proposals = self.obj.user.speaker_at.filter(
            ~(Proposal.state.DRAFT), ~(Proposal.state.DELETED)
        ).all()

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
        past_projects = projects.filter(
            Project.state.PUBLISHED, Project.schedule_state.PAST
        ).order_by(Project.schedule_start_at.desc())
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
                    'datetime': date_filter(
                        p.schedule_end_at_localized, format='dd MMM yyyy'
                    ),
                    'venue': p.primary_venue.city if p.primary_venue else p.location,
                    'url': p.url_for(),
                }
                for p in pagination.items
            ],
        }

    @route('edit', methods=['GET', 'POST'])
    @requires_roles({'admin'})
    def edit(self):
        form = ProfileForm(obj=self.obj, model=Profile)
        if self.obj.user:
            form.make_for_user()
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return redirect(self.obj.url_for(), code=303)
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
        form = ProfileLogoForm()
        edit_logo_url = self.obj.url_for('edit_logo_url')
        return {
            'edit_logo_url': edit_logo_url,
            'form': form,
        }

    @route('edit_logo', methods=['GET', 'POST'])
    @requires_roles({'admin'})
    def edit_logo_url(self):
        form = ProfileLogoForm(obj=self.obj)
        if request.method == 'POST':
            if form.validate_on_submit():
                form.populate_obj(self.obj)
                db.session.commit()
                flash(_("Your changes have been saved"), 'info')
                return render_redirect(self.obj.url_for(), code=303)
            else:
                return render_form(
                    form=form, title="", submit=_("Save logo"), ajax=True
                )
        return render_form(
            form=form,
            title="",
            submit=_("Save logo"),
            ajax=True,
            template='img_upload_formlayout.html.jinja2',
        )

    @route('update_banner', methods=['GET', 'POST'])
    @render_with('update_logo_modal.html.jinja2')
    @requires_roles({'admin'})
    def update_banner(self):
        form = ProfileBannerForm()
        edit_logo_url = self.obj.url_for('edit_banner_image_url')
        return {
            'edit_logo_url': edit_logo_url,
            'form': form,
        }

    @route('edit_banner', methods=['GET', 'POST'])
    @requires_roles({'admin'})
    def edit_banner_image_url(self):
        form = ProfileBannerForm(obj=self.obj)
        if request.method == 'POST':
            if form.validate_on_submit():
                form.populate_obj(self.obj)
                db.session.commit()
                flash(_("Your changes have been saved"), 'info')
                return render_redirect(self.obj.url_for(), code=303)
            else:
                return render_form(
                    form=form, title="", submit=_("Save banner"), ajax=True
                )
        return render_form(
            form=form,
            title="",
            submit=_("Save banner"),
            ajax=True,
            template='img_upload_formlayout.html.jinja2',
        )

    @route('transition', methods=['POST'])
    @requires_login
    @requires_roles({'owner'})
    def transition(self):
        form = self.obj.forms.transition(obj=self.obj)
        if form.validate_on_submit():
            transition_name = form.transition.data
            getattr(self.obj, transition_name)()
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
        else:
            flash(
                _("There was a problem saving your changes. Please try again"), 'error'
            )
        return redirect(get_next_url(referrer=True), code=303)


@route('/', subdomain='<profile>')
class FunnelProfileView(ProfileView):
    @route('')
    @render_with('funnelindex.html.jinja2')
    @requires_roles({'reader'})
    def view(self):
        return {'profile': self.obj, 'projects': self.obj.listed_projects}


ProfileView.init_app(app)
FunnelProfileView.init_app(funnelapp)
