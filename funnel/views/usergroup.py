# -*- coding: utf-8 -*-

from flask import render_template, redirect, request
from coaster.views import load_models
from baseframe import _
from baseframe.forms import render_form, render_delete_sqla

from .. import funnelapp, app, lastuser
from ..models import db, Profile, User, UserGroup, ProposalSpace, ProposalSpaceRedirect
from ..forms import UserGroupForm


@app.route('/<profile>/<space>/users')
@funnelapp.route('/<space>/users', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view-usergroup')
def usergroup_list(profile, space):
    return render_template('usergroups.html.jinja2', space=space, usergroups=space.usergroups)


@app.route('/<profile>/<space>/users/<group>')
@funnelapp.route('/<space>/users/<group>', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (UserGroup, {'name': 'group', 'proposal_space': 'space'}, 'usergroup'),
    permission='view-usergroup')
def usergroup_view(profile, space, usergroup):
    return render_template('usergroup.html.jinja2', space=space, usergroup=usergroup)


@app.route('/<profile>/<space>/users/new', defaults={'group': None}, endpoint='usergroup_new',
    methods=['GET', 'POST'])
@funnelapp.route('/<space>/users/new', defaults={'group': None}, endpoint='usergroup_new',
    methods=['GET', 'POST'], subdomain='<profile>')
@app.route('/<profile>/<space>/users/<group>/edit', methods=['GET', 'POST'])
@funnelapp.route('/<space>/users/<group>/edit', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='new-usergroup', kwargs=True)
def usergroup_edit(profile, space, kwargs):
    group = kwargs.get('group')
    form = UserGroupForm(model=UserGroup, parent=space)
    if group is not None:
        usergroup = UserGroup.query.filter_by(name=group, proposal_space=space).first_or_404()
        form.edit_id = usergroup.id
        if request.method == 'GET':
            form.name.data = usergroup.name
            form.title.data = usergroup.title
            form.users.data = usergroup.users
    if form.validate_on_submit():
        if group is None:
            usergroup = UserGroup(proposal_space=space)
        usergroup.name = form.name.data
        usergroup.title = form.title.data
        usergroup.users = form.users.data
        db.session.commit()
        return redirect(usergroup.url_for(), code=303)
    if group is None:
        return render_form(form=form, title=_("New user group"), submit=_("Create user group"))

    else:
        return render_form(form=form, title=_("Edit user group"), submit=_("Save changes"))


@app.route('/<profile>/<space>/users/<group>/delete', methods=['GET', 'POST'])
@funnelapp.route('/<space>/users/<group>/delete', methods=['GET', 'POST'], subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (UserGroup, {'name': 'group', 'proposal_space': 'space'}, 'usergroup'),
    permission='delete-usergroup')
def usergroup_delete(profile, space, usergroup):
    return render_delete_sqla(usergroup, db, title=_(u"Confirm delete"),
        message=_(u"Do you really wish to delete user group ‘{title}’?").format(title=usergroup.title),
        success=_("Your user group has been deleted"),
        next=space.url_for('usergroups'),
        cancel_url=space.url_for('usergroups'))
