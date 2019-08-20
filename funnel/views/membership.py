# -*- coding: utf-8 -*-

from flask import flash, g, redirect, request
from werkzeug.datastructures import MultiDict

from baseframe import _, forms
from baseframe.forms import render_form
from coaster.views import ModelView, UrlForView, render_with, requires_permission, route

from .. import app, funnelapp, lastuser
from ..forms import LabelForm, LabelOptionForm, SavedProjectForm
from ..models import Label, Profile, Project, db
from .decorators import legacy_redirect
from .mixins import ProjectViewMixin


def labels_list_data(labels):
    data = []
    for label in labels:
        data.append({
            'title': label.title,
            'edit_url': label.url_for('edit'),
            'delete_url': label.url_for('delete')
        })
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
        return {'project': self.obj,
            'labels': labels_list_data(
                self.obj.labels
            ),
            'project_save_form': project_save_form}

    @route('new', methods=['GET', 'POST'])
    @render_with('membership.html.jinja2', json=True)
    @lastuser.requires_login
    @requires_permission('admin')
    def new_member(self):
        print 'new', request.is_xhr
        if request.is_xhr:
            form = LabelForm(model=Label, parent=self.obj.parent)
            html_form = render_form(form=form, title=_("New member"), ajax=False, with_chrome=False)
            return {'form': html_form}


@route('/<project>/membership', subdomain='<profile>')
class FunnelProjectMembershipView(ProjectMembershipView):
    pass


ProjectMembershipView.init_app(app)
FunnelProjectMembershipView.init_app(funnelapp)
