# -*- coding: utf-8 -*-

from flask import render_template, redirect, request
from coaster.views import load_models
from baseframe import _
from baseframe.forms import render_form, render_delete_sqla

from .. import app, lastuser
from ..models import db, Profile, User, UserGroup, ProposalSpace, ProposalSpaceRedirect
from ..forms import UserGroupForm


@app.route('/<space>/users', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    permission='view-usergroup')
def usergroup_list(profile, space):
    return render_template('usergroups.html', space=space, usergroups=space.usergroups)


@app.route('/<space>/users/<group>', subdomain='<profile>')
@lastuser.requires_login
@load_models(
    (Profile, {'name': 'profile'}, 'g.profile'),
    ((ProposalSpace, ProposalSpaceRedirect), {'name': 'space', 'profile': 'profile'}, 'space'),
    (UserGroup, {'name': 'group', 'proposal_space': 'space'}, 'usergroup'),
    permission='view-usergroup')
def usergroup_view(profile, space, usergroup):
    return render_template('usergroup.html', space=space, usergroup=usergroup)


@app.route('/<space>/users/new',
    defaults={'group': None},
    endpoint='usergroup_new',
    methods=['GET', 'POST'],
    subdomain='<profile>')
@app.route('/<space>/users/<group>/edit', methods=['GET', 'POST'], subdomain='<profile>')
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
            form.users.data = '\r\n'.join([u.email or u.username or '' for u in usergroup.users])
    if form.validate_on_submit():
        if group is None:
            usergroup = UserGroup(proposal_space=space)
        usergroup.name = form.name.data
        usergroup.title = form.title.data
        formdata = [line.strip() for line in
            form.users.data.replace('\r', '\n').replace(',', '\n').split('\n') if line]
        usersdata = lastuser.getusers(names=formdata)
        users = []
        for userdata in usersdata or []:
            user = User.query.filter_by(userid=userdata['userid']).first()
            if user is None:
                user = User(userid=userdata['userid'], fullname=userdata['title'])
                db.session.add(user)
            users.append(user)
        usergroup.users = users
        db.session.commit()
        return redirect(usergroup.url_for(), code=303)
    if group is None:
        return render_form(form=form, title=_("New user group"), submit=_("Create user group"))

    else:
        return render_form(form=form, title=_("Edit user group"), submit=_("Save changes"))


@app.route('/<space>/users/<group>/delete', methods=['GET', 'POST'], subdomain='<profile>')
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
