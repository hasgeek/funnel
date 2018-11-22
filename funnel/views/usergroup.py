# -*- coding: utf-8 -*-

from flask import render_template, redirect, request
from coaster.views import load_models
from baseframe import _
from baseframe.forms import render_form, render_delete_sqla

from .. import app, funnelapp, lastuser
from ..models import db, Profile, User, UserGroup, Project, ProjectRedirect
from ..forms import UserGroupForm


@app.route('/<profile>/<project>/users')
@funnelapp.route('/<project>/users', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='view-usergroup')
def usergroup_list(profile, project):
    return render_template('usergroups.html.jinja2', project=project, usergroups=project.usergroups)


@app.route('/<profile>/<project>/users/<group>')
@funnelapp.route('/<project>/users/<group>', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (UserGroup, {'name': 'group', 'project': 'project'}, 'usergroup'),
    permission='view-usergroup')
def usergroup_view(profile, project, usergroup):
    return render_template('usergroup.html.jinja2', project=project, usergroup=usergroup)


@app.route('/<profile>/<project>/users/new', defaults={'group': None}, endpoint='usergroup_new', methods=['GET', 'POST'])
@app.route('/<profile>/<project>/users/<group>/edit', methods=['GET', 'POST'])
@funnelapp.route('/<project>/users/new', defaults={'group': None}, endpoint='usergroup_new', methods=['GET', 'POST'], subdomain='<profile>')
@funnelapp.route('/<project>/users/<group>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    permission='new-usergroup', kwargs=True)
def usergroup_edit(profile, project, kwargs):
    group = kwargs.get('group')
    form = UserGroupForm(model=UserGroup, parent=project)
    if group is not None:
        usergroup = UserGroup.query.filter_by(name=group, project=project).first_or_404()
        form.edit_id = usergroup.id
        if request.method == 'GET':
            form.name.data = usergroup.name
            form.title.data = usergroup.title
            form.users.data = usergroup.users
    if form.validate_on_submit():
        if group is None:
            usergroup = UserGroup(project=project)
        usergroup.name = form.name.data
        usergroup.title = form.title.data
        usergroup.users = form.users.data
        db.session.commit()
        return redirect(usergroup.url_for(), code=303)
    if group is None:
        return render_form(form=form, title=_("New user group"), submit=_("Create user group"))

    else:
        return render_form(form=form, title=_("Edit user group"), submit=_("Save changes"))


@app.route('/<profile>/<project>/users/<group>/delete', methods=['GET', 'POST'])
@funnelapp.route('/<project>/users/<group>/delete', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((Project, ProjectRedirect), {'name': 'project', 'profile': 'profile'}, 'project'),
    (UserGroup, {'name': 'group', 'project': 'project'}, 'usergroup'),
    permission='delete-usergroup')
def usergroup_delete(profile, project, usergroup):
    return render_delete_sqla(usergroup, db, title=_(u"Confirm delete"),
        message=_(u"Do you really wish to delete user group ‘{title}’?").format(title=usergroup.title),
        success=_("Your user group has been deleted"),
        next=project.url_for('usergroups'),
        cancel_url=project.url_for('usergroups'))
