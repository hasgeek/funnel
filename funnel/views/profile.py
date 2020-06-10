from flask import flash, redirect

from baseframe import _
from baseframe.forms import render_form
from coaster.auth import current_auth
from coaster.views import (
    ModelView,
    UrlForView,
    get_next_url,
    render_with,
    requires_roles,
    route,
)

from .. import app, funnelapp
from ..forms import ProfileForm, SavedProjectForm
from ..models import Profile, Project, db
from .decorators import legacy_redirect
from .helpers import requires_login
from .mixins import ProfileViewMixin


@Profile.views('main')
@route('/<profile>')
class ProfileView(ProfileViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('')
    @render_with('index.html.jinja2', json=True)
    @requires_roles({'reader', 'admin'})
    def view(self):
        # `order_by(None)` clears any existing order defined in relationship.
        # We're using it because we want to define our own order here.
        projects = self.obj.listed_projects.order_by(None)
        past_projects = (
            projects.filter(Project.state.PUBLISHED, Project.schedule_state.PAST)
            .order_by(Project.schedule_start_at.desc())
            .all()
        )
        all_projects = (
            projects.filter(
                Project.state.PUBLISHED,
                db.or_(Project.schedule_state.LIVE, Project.schedule_state.UPCOMING),
            )
            .order_by(Project.schedule_start_at.asc())
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
            .order_by(Project.schedule_start_at.asc())
            .limit(1)
            .first()
        )
        unscheduled_projects = projects.filter(
            Project.schedule_state.PUBLISHED_WITHOUT_SESSIONS
        ).all()
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
        else:
            draft_projects = self.obj.draft_projects_for(current_auth.user)

        return {
            'profile': self.obj.current_access(datasets=('primary', 'related')),
            'past_projects': [
                p.current_access(datasets=('without_parent', 'related'))
                for p in past_projects
            ],
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
                featured_project.current_access(datasets=('without_parent', 'related'))
                if featured_project
                else None
            ),
            'project_save_form': SavedProjectForm(),
        }

    @route('edit', methods=['GET', 'POST'])
    @requires_roles({'admin'})
    def edit(self):
        form = ProfileForm(obj=self.obj, model=Profile)
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
