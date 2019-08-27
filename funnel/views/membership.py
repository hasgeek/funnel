# -*- coding: utf-8 -*-

from flask import request

from baseframe import _
from baseframe.forms import render_form
from coaster.auth import current_auth
from coaster.views import ModelView, UrlForView, render_with, requires_permission, route

from .. import app, funnelapp, lastuser
from ..forms import ProjectMembershipForm, SavedProjectForm
from ..models import ProjectCrewMembership, db
from .decorators import legacy_redirect
from .mixins import ProjectViewMixin


def labels_list_data(labels):
    data = []
    for label in labels:
        data.append(
            {
                'title': label.title,
                'edit_url': label.url_for('edit'),
                'delete_url': label.url_for('delete'),
            }
        )
    return data


@route('/<profile>/<project>/membership')
class ProjectMembershipView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('', methods=['GET', 'POST'])
    @render_with('membership.html.jinja2')
    @lastuser.requires_login
    @requires_permission('edit_project')
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
    @requires_permission('admin')
    def new_member(self):
        membership_form = ProjectMembershipForm()

        if request.method == 'POST':
            if membership_form.validate_on_submit():
                previous_membership = (
                    ProjectCrewMembership.query.filter(ProjectCrewMembership.active)
                    .filter_by(project=self.obj, user=membership_form.user.data)
                    .one_or_none()
                )
                if previous_membership is not None:
                    new_membership = previous_membership.replace(
                        actor=current_auth.user,
                        is_editor=membership_form.is_editor.data,
                        is_concierge=membership_form.is_concierge.data,
                        is_usher=membership_form.is_usher.data,
                    )
                else:
                    new_membership = ProjectCrewMembership(project=self.obj)
                    membership_form.populate_obj(new_membership)
                    db.session.add(new_membership)
                db.session.commit()

                return {
                    'status': 'ok',
                    'memberships': [
                        membership.current_access()
                        for membership in self.obj.active_crew_memberships
                    ],
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
        return {'status': 'ok', 'form': membership_form_html}


@route('/<project>/membership', subdomain='<profile>')
class FunnelProjectMembershipView(ProjectMembershipView):
    pass


ProjectMembershipView.init_app(app)
FunnelProjectMembershipView.init_app(funnelapp)
