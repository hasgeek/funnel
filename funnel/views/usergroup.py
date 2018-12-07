# -*- coding: utf-8 -*-

from flask import render_template, redirect, request
from coaster.views import load_models, route, render_with, requires_permission, UrlForView, ModelView
from baseframe import _
from baseframe.forms import render_form, render_delete_sqla

from .. import app, funnelapp, lastuser
from ..models import db, Profile, UserGroup, Project, ProjectRedirect
from ..forms import UserGroupForm
from .mixins import ProjectViewMixin, UserGroupViewMixin


@route('/<profile>/<project>/users')
class ProjectUsergroupView(ProjectViewMixin, UrlForView, ModelView):
    @route('')
    @render_with('usergroups.html.jinja2')
    @lastuser.requires_login
    @requires_permission('view-usergroup')
    def usergroups(self):
        return dict(project=self.obj, usergroups=self.obj.usergroups)

    @route('new', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('new-usergroup')
    def new_usergroup(self):
        form = UserGroupForm(model=UserGroup, parent=self.obj)
        if form.validate_on_submit():
            usergroup = UserGroup(project=self.obj)
            usergroup.name = form.name.data
            usergroup.title = form.title.data
            usergroup.users = form.users.data
            db.session.commit()
            return redirect(usergroup.url_for(), code=303)
        return render_form(form=form, title=_("New user group"), submit=_("Create user group"))


@route('/<project>/users', subdomain='<profile>')
class FunnelProjectUsergroupView(ProjectUsergroupView):
    pass


ProjectUsergroupView.init_app(app)
FunnelProjectUsergroupView.init_app(funnelapp)


@route('/<profile>/<project>/users/<group>')
class UserGroupView(UserGroupViewMixin, UrlForView, ModelView):
    @route('')
    @render_with('usergroup.html.jinja2')
    @requires_permission('view-usergroup')
    def view(self):
        return dict(project=self.obj.project, usergroup=self.obj)

    @route('edit', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('new-usergroup')
    def edit(self):
        form = UserGroupForm(model=UserGroup, object=self.obj, parent=self.obj.project)
        if form.validate_on_submit():
            self.obj.name = form.name.data
            self.obj.title = form.title.data
            self.obj.users = form.users.data
            db.session.commit()
            return redirect(self.obj.url_for(), code=303)
        else:
            return render_form(form=form, title=_("Edit user group"), submit=_("Save changes"))

    @route('delete', methods=['GET', 'POST'])
    @lastuser.requires_login
    @requires_permission('delete-usergroup')
    def delete(self):
        return render_delete_sqla(self.obj, db, title=_(u"Confirm delete"),
            message=_(u"Do you really wish to delete user group ‘{title}’?").format(title=self.obj.title),
            success=_("Your user group has been deleted"),
            next=self.obj.project.url_for('usergroups'),
            cancel_url=self.obj.project.url_for('usergroups'))


@route('/<project>/users/<group>', subdomain='<profile>')
class FunnelUserGroupView(UserGroupView):
    pass


UserGroupView.init_app(app)
FunnelUserGroupView.init_app(funnelapp)
