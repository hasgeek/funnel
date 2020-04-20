# -*- coding: utf-8 -*-

from flask import flash, redirect

from baseframe import _
from baseframe.forms import render_form
from coaster.views import ModelView, UrlForView, render_with, requires_roles, route

from .. import app, funnelapp
from ..forms import EditProfileForm, SavedProjectForm
from ..models import Profile, Project, db
from .decorators import legacy_redirect
from .mixins import ProfileViewMixin


@route('/<profile>')
class ProfileView(ProfileViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('')
    @render_with('index.html.jinja2', json=True)
    @requires_roles({'reader'})
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
        if featured_project in upcoming_projects:
            upcoming_projects.remove(featured_project)
        open_cfp_projects = (
            projects.filter(Project.state.PUBLISHED, Project.cfp_state.OPEN)
            .order_by(Project.schedule_start_at.asc())
            .all()
        )
        draft_projects = self.obj.draft_projects if self.obj.current_roles.admin else []

        return {
            'profile': self.obj.current_access(),
            'past_projects': [p.current_access() for p in past_projects],
            'all_projects': [p.current_access() for p in all_projects],
            'upcoming_projects': [p.current_access() for p in upcoming_projects],
            'open_cfp_projects': [p.current_access() for p in open_cfp_projects],
            'draft_projects': [p.current_access() for p in draft_projects],
            'featured_project': (
                featured_project.current_access() if featured_project else None
            ),
            'project_save_form': SavedProjectForm(),
        }

    @route('edit', methods=['GET', 'POST'])
    @requires_roles({'admin'})
    def edit(self):
        form = EditProfileForm(obj=self.obj, model=Profile)
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


@route('/', subdomain='<profile>')
class FunnelProfileView(ProfileView):
    @route('')
    @render_with('funnelindex.html.jinja2')
    @requires_roles({'reader'})
    def view(self):
        return {'profile': self.obj, 'projects': self.obj.listed_projects}


ProfileView.init_app(app)
FunnelProfileView.init_app(funnelapp)
