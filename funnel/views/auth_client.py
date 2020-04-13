# -*- coding: utf-8 -*-

from flask import abort, flash, render_template, request, url_for

from baseframe import _
from baseframe.forms import render_delete_sqla, render_form, render_redirect
from coaster.auth import current_auth
from coaster.views import ModelView, UrlForView, render_with, requires_permission, route

from .. import app
from ..forms import (
    ClientCredentialForm,
    PermissionEditForm,
    RegisterClientForm,
    TeamPermissionAssignForm,
    UserPermissionAssignForm,
)
from ..models import (
    AuthClient,
    AuthClientCredential,
    AuthClientTeamPermissions,
    AuthClientUserPermissions,
    Team,
    User,
    db,
)
from .helpers import requires_login

# --- Routes: client apps -----------------------------------------------------


@app.route('/account/apps')
@requires_login
def client_list():
    if current_auth.is_authenticated:
        return render_template(
            'auth_client_index.html.jinja2',
            auth_clients=AuthClient.all_for(current_auth.user),
        )
    else:
        # TODO: Show better UI for non-logged in users
        return render_template('client_list.html.jinja2', clients=[])


@app.route('/account/apps/all')
def client_list_all():
    return render_template(
        'auth_client_index.html.jinja2', auth_clients=AuthClient.all_for(None)
    )


def available_client_owners():
    """
    Return a list of possible client owners for the current user.
    """
    choices = []
    choices.append((current_auth.user.buid, current_auth.user.pickername))
    for org in current_auth.user.organizations_owned():
        choices.append((org.buid, org.pickername))
    return choices


@app.route('/account/apps/new', methods=['GET', 'POST'])
@requires_login
def client_new():
    form = RegisterClientForm(model=AuthClient)
    form.edit_user = current_auth.user
    form.client_owner.choices = available_client_owners()
    if request.method == 'GET':
        form.client_owner.data = current_auth.user.buid

    if form.validate_on_submit():
        auth_client = AuthClient()
        form.populate_obj(auth_client)
        auth_client.user = form.user
        auth_client.organization = form.organization
        auth_client.trusted = False
        db.session.add(auth_client)
        db.session.commit()
        return render_redirect(auth_client.url_for('info'), code=303)

    return render_form(
        form=form,
        title=_("Register a new client application"),
        formid='client_new',
        submit=_("Register application"),
        ajax=True,
    )


@route('/account/apps/<key>')
class AuthClientView(UrlForView, ModelView):
    model = AuthClient
    route_model_map = {'key': 'buid'}

    def loader(self, key):
        return self.model.query.filter(AuthClient.buid == key).first_or_404()

    @route('', methods=['GET'])
    @render_with('auth_client.html.jinja2')
    @requires_permission('view')
    def info(self):
        if self.obj.user:
            permassignments = AuthClientUserPermissions.all_forclient(self.obj).all()
        else:
            permassignments = AuthClientTeamPermissions.all_forclient(self.obj).all()
        return {
            'auth_client': self.obj,
            'permassignments': permassignments,
        }

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('edit')
    def edit(self):
        form = RegisterClientForm(obj=self.obj, model=AuthClient)
        form.edit_user = current_auth.user
        form.client_owner.choices = available_client_owners()
        if request.method == 'GET':
            if self.obj.user:
                form.client_owner.data = self.obj.user.buid
            else:
                form.client_owner.data = self.obj.organization.buid

        if form.validate_on_submit():
            if self.obj.user != form.user or self.obj.organization != form.organization:
                # Ownership has changed. Remove existing permission assignments
                AuthClientUserPermissions.all_forclient(self.obj).delete(
                    synchronize_session=False
                )
                AuthClientTeamPermissions.all_forclient(self.obj).delete(
                    synchronize_session=False
                )
                flash(
                    _(
                        "This application’s owner has changed, so all previously assigned permissions "
                        "have been revoked"
                    ),
                    'warning',
                )
            form.populate_obj(self.obj)
            self.obj.user = form.user
            self.obj.organization = form.organization
            db.session.commit()
            return render_redirect(self.obj.url_for('`info'), code=303)

        return render_form(
            form=form,
            title=_("Edit application"),
            formid='client_edit',
            submit=_("Save changes"),
            ajax=True,
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('delete')
    def delete(self):
        return render_delete_sqla(
            self.obj,
            db,
            title=_("Confirm delete"),
            message=_("Delete application ‘{title}’? ").format(title=self.obj.title),
            success=_(
                "You have deleted application ‘{title}’ and all its associated resources and permission assignments"
            ).format(title=self.obj.title),
            next=url_for('client_list'),
        )

    @route('cred', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('edit')
    def cred_new(self):
        form = ClientCredentialForm()
        if request.method == 'GET' and not self.obj.credentials:
            form.title.data = _("Default")
        if form.validate_on_submit():
            cred, secret = AuthClientCredential.new(self.obj)
            cred.title = form.title.data
            db.session.commit()
            return render_template(
                'auth_client_credential.html.jinja2',
                name=cred.name,
                secret=secret,
                cred=cred,
            )
        return render_form(
            form=form,
            title=_("New access key"),
            formid='client_cred',
            submit=_("Create"),
            ajax=False,
        )

    @route('perms/new', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('assign-permissions')
    def permission_user_new(self):
        if self.obj.user:
            form = UserPermissionAssignForm()
        elif self.obj.organization:
            form = TeamPermissionAssignForm()
            form.organization = self.obj.organization
            form.team_id.choices = [
                (team.buid, team.title) for team in self.obj.organization.teams
            ]
        else:
            abort(403)  # This should never happen. Clients always have an owner.
        if form.validate_on_submit():
            perms = set()
            if self.obj.user:
                permassign = AuthClientUserPermissions.get(
                    auth_client=self.obj, user=form.user.data
                )
                if permassign:
                    perms.update(permassign.access_permissions.split())
                else:
                    permassign = AuthClientUserPermissions(
                        user=form.user.data, auth_client=self.obj
                    )
                    db.session.add(permassign)
            else:
                permassign = AuthClientTeamPermissions.get(
                    auth_client=self.obj, team=form.team
                )
                if permassign:
                    perms.update(permassign.access_permissions.split())
                else:
                    permassign = AuthClientTeamPermissions(
                        team=form.team, auth_client=self.obj
                    )
                    db.session.add(permassign)
            perms.update(form.perms.data.split())
            permassign.access_permissions = ' '.join(sorted(perms))
            db.session.commit()
            if self.obj.user:
                flash(
                    _("Permissions have been assigned to user {pname}").format(
                        pname=form.user.data.pickername
                    ),
                    'success',
                )
            else:
                flash(
                    _("Permissions have been assigned to team ‘{pname}’").format(
                        pname=permassign.team.pickername
                    ),
                    'success',
                )
            return render_redirect(self.obj.url_for('info'), code=303)
        return render_form(
            form=form,
            title=_("Assign permissions"),
            formid='perm_assign',
            submit=_("Assign permissions"),
        )


AuthClientView.init_app(app)

# --- Routes: client credentials ----------------------------------------------


@route('/apps/<key>/cred/<name>')
class AuthClientCredentialView(UrlForView, ModelView):
    model = AuthClientCredential
    route_model_map = {'key': 'auth_client.buid', 'name': 'name'}

    def loader(self, key, name):
        cred = (
            self.model.query.join(AuthClient)
            .filter(AuthClient.buid == key, AuthClientCredential.name == name)
            .first_or_404()
        )
        return cred

    @route('delete', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('delete')
    def delete(self):
        return render_delete_sqla(
            self.obj,
            db,
            title=_("Confirm delete"),
            message=_("Delete access key ‘{title}’? ").format(title=self.obj.title),
            success=_("You have deleted access key ‘{title}’").format(
                title=self.obj.title
            ),
            next=self.obj.auth_client.url_for('info'),
        )


AuthClientCredentialView.init_app(app)


# --- Routes: client app permissions ------------------------------------------


@route('/apps/<key>/perms/u/<buid>')
class AuthClientUserPermissionsView(UrlForView, ModelView):
    model = AuthClientUserPermissions
    route_model_map = {'key': 'auth_client.buid', 'buid': 'user.buid'}

    def loader(self, key, buid):
        user = User.get(buid=buid)
        perm = (
            self.model.query.join(AuthClient)
            .filter(AuthClient.buid == key, self.model.user == user)
            .one_or_404()
        )
        return perm

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('assign-permissions')
    def edit(self):
        form = PermissionEditForm()
        if request.method == 'GET':
            if self.obj:
                form.perms.data = self.obj.access_permissions
        if form.validate_on_submit():
            perms = ' '.join(sorted(form.perms.data.split()))
            if not perms:
                db.session.delete(self.obj)
            else:
                self.obj.access_permissions = perms
            db.session.commit()
            if perms:
                flash(
                    _("Permissions have been updated for user {pname}").format(
                        pname=self.obj.user.pickername
                    ),
                    'success',
                )
            else:
                flash(
                    _("All permissions have been revoked for user {pname}").format(
                        pname=self.obj.user.pickername
                    ),
                    'success',
                )
            return render_redirect(self.obj.auth_client.url_for('info'), code=303)
        return render_form(
            form=form,
            title=_("Edit permissions"),
            formid='perm_edit',
            submit=_("Save changes"),
            ajax=True,
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('assign-permissions')
    def delete(self):
        return render_delete_sqla(
            self.obj,
            db,
            title=_("Confirm delete"),
            message=_(
                "Remove all permissions assigned to user {pname} for app ‘{title}’?"
            ).format(pname=self.obj.user.pickername, title=self.obj.auth_client.title),
            success=_("You have revoked permisions for user {pname}").format(
                pname=self.obj.user.pickername
            ),
            next=self.obj.auth_client.url_for('info'),
        )


AuthClientUserPermissionsView.init_app(app)


@route('/apps/<key>/perms/t/<buid>')
class AuthClientTeamPermissionsView(UrlForView, ModelView):
    model = AuthClientTeamPermissions
    route_model_map = {'key': 'auth_client.buid', 'buid': 'team.buid'}

    def loader(self, key, buid):
        team = Team.get(buid=buid)
        perm = (
            self.model.query.join(AuthClient)
            .filter(AuthClient.buid == key, self.model.team == team)
            .one_or_404()
        )
        return perm

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('assign-permissions')
    def edit(self):
        form = PermissionEditForm()
        if request.method == 'GET':
            if self.obj:
                form.perms.data = self.obj.access_permissions
        if form.validate_on_submit():
            perms = ' '.join(sorted(form.perms.data.split()))
            if not perms:
                db.session.delete(self.obj)
            else:
                self.obj.access_permissions = perms
            db.session.commit()
            if perms:
                flash(
                    _("Permissions have been updated for team {title}").format(
                        title=self.obj.team.title
                    ),
                    'success',
                )
            else:
                flash(
                    _("All permissions have been revoked for team {title}").format(
                        title=self.obj.team.title
                    ),
                    'success',
                )
            return render_redirect(self.obj.auth_client.url_for('info'), code=303)
        return render_form(
            form=form,
            title=_("Edit permissions"),
            formid='perm_edit',
            submit=_("Save changes"),
            ajax=True,
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('assign-permissions')
    def delete(self):
        return render_delete_sqla(
            self.obj,
            db,
            title=_("Confirm delete"),
            message=_(
                "Remove all permissions assigned to team ‘{pname}’ for app ‘{title}’?"
            ).format(pname=self.obj.team.title, title=self.obj.auth_client.title),
            success=_("You have revoked permisions for team {title}").format(
                title=self.obj.team.title
            ),
            next=self.obj.auth_client.url_for('info'),
        )


AuthClientTeamPermissionsView.init_app(app)
