# -*- coding: utf-8 -*-

from flask import g, request

from baseframe import _
from baseframe.forms import Form, render_form
from coaster.auth import current_auth
from coaster.views import (
    ModelView,
    UrlChangeCheck,
    UrlForView,
    render_with,
    requires_roles,
    route,
)

from .. import app, funnelapp, lastuser
from ..forms import ProjectMembershipForm, SavedProjectForm
from ..models import Profile, Project, ProjectCrewMembership, db
from .decorators import legacy_redirect
from .mixins import ProjectViewMixin


@route('/<profile>/<project>/membership')
class ProjectMembershipView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('', methods=['GET', 'POST'])
    @render_with('membership.html.jinja2')
    @lastuser.requires_login
    @requires_roles({'profile_admin'})
    def membership(self):
        project_save_form = SavedProjectForm()
        return {
            'project': self.obj,
            'memberships': [
                membership.current_access()
                for membership in self.obj.active_crew_memberships
            ],
            'project_save_form': project_save_form,
        }

    @route('new', methods=['GET', 'POST'])
    @render_with(json=True)
    @lastuser.requires_login
    @requires_roles({'profile_admin'})
    def new_member(self):
        membership_form = ProjectMembershipForm()

        if request.method == 'POST':
            if membership_form.validate_on_submit():
                previous_membership = (
                    ProjectCrewMembership.query.filter(ProjectCrewMembership.active)
                    .filter_by(project=self.obj, user=membership_form.user.data)
                    .one_or_none()
                )
                if previous_membership is None:
                    new_membership = ProjectCrewMembership(project=self.obj)
                    membership_form.populate_obj(new_membership)
                    db.session.add(new_membership)
                    db.session.commit()
                    return {'status': 'ok'}
                else:
                    return {
                        'status': 'ok',
                        'message': _("Member already exists in the project"),
                    }
            else:
                return (
                    {
                        'status': 'error',
                        'message': _("The new member could not be added"),
                        'errors': membership_form.errors,
                    },
                    400,
                )

        membership_form_html = render_form(
            form=membership_form, title=_("New member"), ajax=False, with_chrome=False
        )
        return {'form': membership_form_html}


@route('/<project>/membership', subdomain='<profile>')
class FunnelProjectMembershipView(ProjectMembershipView):
    pass


ProjectMembershipView.init_app(app)
FunnelProjectMembershipView.init_app(funnelapp)


@route('/<profile>/<project>/membership/<suuid>')
class ProjectCrewMembershipView(UrlChangeCheck, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]
    model = ProjectCrewMembership

    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'suuid': 'suuid',
    }

    def loader(self, profile, project, suuid):
        membership = (
            self.model.query.join(Project, Profile)
            .filter(
                Profile.name == profile,
                Project.name == project,
                ProjectCrewMembership.suuid == suuid,
            )
            .first_or_404()
        )
        return membership

    def after_loader(self):
        g.profile = self.obj.project.profile
        super(ProjectCrewMembershipView, self).after_loader()

    @route('edit', methods=['GET', 'POST'])
    @render_with(json=True)
    @lastuser.requires_login
    @requires_roles({'profile_admin'})
    def edit(self):
        previous_membership = self.obj

        membership_form = ProjectMembershipForm(obj=previous_membership)

        if membership_form.validate_on_submit():
            previous_membership.replace(
                actor=current_auth.user,
                is_editor=membership_form.is_editor.data,
                is_concierge=membership_form.is_concierge.data,
                is_usher=membership_form.is_usher.data,
            )
            db.session.commit()
            return {'status': 'ok'}

        membership_form_html = render_form(
            form=membership_form, title=_("Edit member"), ajax=False, with_chrome=False
        )
        return {'form': membership_form_html}

    @route('delete', methods=['POST'])
    @render_with(json=True)
    @lastuser.requires_login
    @requires_roles({'profile_admin'})
    def delete(self):
        form = Form()
        if form.validate_on_submit():
            previous_membership = self.obj
            if previous_membership is None:
                return (
                    {
                        'status': 'error',
                        'message': _("Member does not exist in this project"),
                    },
                    400,
                )
            else:
                previous_membership.revoke(actor=current_auth.user)
                db.session.commit()
                return {'status': 'ok'}
        else:
            return ({'status': 'error', 'errors': form.errors}, 400)


@route('/<project>/membership/<suuid>', subdomain='<profile>')
class FunnelProjectCrewMembershipView(ProjectCrewMembershipView):
    pass


ProjectCrewMembershipView.init_app(app)
FunnelProjectCrewMembershipView.init_app(funnelapp)
