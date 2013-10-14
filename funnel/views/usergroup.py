# -*- coding: utf-8 -*-

from flask import render_template, redirect, request, flash
from coaster.views import load_models, load_model
from baseframe import _

from .. import app, lastuser
from ..models import db, User, UserGroup, ProposalSpace
from ..forms import  UserGroupForm, ConfirmDeleteForm


@app.route('/<space>/users')
@lastuser.requires_login
@load_model(ProposalSpace, {'name': 'space'}, 'space',
    permission=('view-usergroup', 'siteadmin'), addlperms=lastuser.permissions)
def usergroup_list(space):
    return render_template('usergroups.html', space=space, usergroups=space.usergroups,
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('usergroups'), _("Users"))])


@app.route('/<space>/users/<group>')
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (UserGroup, {'name': 'group', 'proposal_space': 'space'}, 'usergroup'),
    permission=('view-usergroup', 'siteadmin'), addlperms=lastuser.permissions)
def usergroup_view(space, usergroup):
    return render_template('usergroup.html', space=space, usergroup=usergroup,
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('usergroups'), _("Users")),
            (usergroup.url_for(), usergroup.title)])


@app.route('/<space>/users/new', defaults={'group': None}, endpoint='usergroup_new', methods=['GET', 'POST'])
@app.route('/<space>/users/<group>/edit', methods=['GET', 'POST'])
@lastuser.requires_login
@load_model(ProposalSpace, {'name': 'space'}, 'space', kwargs=True,
    permission=('new-usergroup', 'siteadmin'), addlperms=lastuser.permissions)
def usergroup_edit(space, kwargs):
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
                user = User(userid=userdata['userid'], username=userdata['name'], fullname=userdata['title'])
                db.session.add(user)
            users.append(user)
        usergroup.users = users
        db.session.commit()
        return redirect(usergroup.url_for(), code=303)
    if group is None:
        return render_template('baseframe/autoform.html', form=form, title=_("New user group"), submit=_("Create user group"),
            breadcrumbs=[
                (space.url_for(), space.title),
                (space.url_for('usergroups'), _("Users"))])

    else:
        return render_template('baseframe/autoform.html', form=form, title=_("Edit user group"), submit=_("Save changes"),
            breadcrumbs=[
                (space.url_for(), space.title),
                (space.url_for('usergroups'), _("Users")),
                (usergroup.url_for(), usergroup.title)])


@app.route('/<space>/users/<group>/delete', methods=['GET', 'POST'])
@lastuser.requires_login
@load_models(
    (ProposalSpace, {'name': 'space'}, 'space'),
    (UserGroup, {'name': 'group', 'proposal_space': 'space'}, 'usergroup'),
    permission=('delete-usergroup', 'siteadmin'), addlperms=lastuser.permissions)
def usergroup_delete(space, usergroup):
    form = ConfirmDeleteForm()
    if form.validate_on_submit():
        if 'delete' in request.form:
            db.session.delete(usergroup)
            db.session.commit()
            flash(_("Your user group has been deleted"), 'info')
            return redirect(space.url_for('usergroups'))
        else:
            return redirect(usergroup.url_for())
    return render_template('delete.html', form=form, title=_(u"Confirm delete"),
        message=_(u"Do you really wish to delete user group ‘{title}’?").format(title=usergroup.title),
        breadcrumbs=[
            (space.url_for(), space.title),
            (space.url_for('usergroups'), _("Users")),
            (usergroup.url_for(), usergroup.title)])
