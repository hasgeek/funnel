# -*- coding: utf-8 -*-

from flask import flash, redirect

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
            'members': [member.current_access() for member in self.obj.crew],
            'project_save_form': project_save_form,
        }

    @route('new', methods=['GET', 'POST'])
    @render_with(json=True)
    @lastuser.requires_login
    @requires_permission('admin')
    def new_member(self):
        membership_form = ProjectMembershipForm()
        if membership_form.validate_on_submit():
            previous_memberships = ProjectCrewMembership.query.filter(
                ProjectCrewMembership.active
            ).filter_by(project=self.obj, user=membership_form.user.data)
            for prevmem in previous_memberships:
                prevmem.revoke(revoked_by=current_auth.user)

            new_membership = ProjectCrewMembership(project=self.obj)
            membership_form.populate_obj(new_membership)
            db.session.add(new_membership)
            db.session.commit()

            flash(_("The new member has been added"), category='success')
            return redirect(self.obj.url_for('membership'), 303)
        else:
            flash(_("The new member could not be added"), category='error')
        membership_form_html = render_form(
            form=membership_form, title=_("New member"), ajax=False, with_chrome=False
        )
        return {'form': membership_form_html}


@route('/<project>/membership', subdomain='<profile>')
class FunnelProjectMembershipView(ProjectMembershipView):
    pass


ProjectMembershipView.init_app(app)
FunnelProjectMembershipView.init_app(funnelapp)
