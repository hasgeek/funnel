from flask import Markup, abort, flash, render_template, request, url_for

from baseframe import _
from baseframe.forms import render_delete_sqla, render_form, render_redirect
from coaster.auth import current_auth
from coaster.views import (
    ClassView,
    ModelView,
    UrlForView,
    render_with,
    requires_permission,
    route,
)

from .. import app
from ..forms import (
    AuthClientCredentialForm,
    AuthClientForm,
    AuthClientPermissionEditForm,
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
from .login_session import requires_login, requires_sudo

# --- Routes: client apps -----------------------------------------------------


@app.route('/apps')
@requires_login
def client_list():
    return render_template(
        'auth_client_index.html.jinja2',
        auth_clients=AuthClient.all_for(current_auth.user),
    )


@app.route('/apps/all')
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
    for org in current_auth.user.organizations_as_owner:
        choices.append((org.buid, org.pickername))
    return choices


@route('/apps/new', methods=['GET', 'POST'])
class AuthClientCreateView(ClassView):
    @route('', endpoint='authclient_new')
    @requires_login
    def new(self):
        form = AuthClientForm(model=AuthClient)
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
            return render_redirect(auth_client.url_for(), code=303)

        return render_form(
            form=form,
            title=_("Register a new client application"),
            formid='client_new',
            submit=_("Register application"),
            ajax=True,
        )


AuthClientCreateView.init_app(app)


@AuthClient.views('main')
@route('/apps/info/<app>')
class AuthClientView(UrlForView, ModelView):
    model = AuthClient
    route_model_map = {'app': 'buid'}

    def loader(self, app):
        return self.model.query.filter(AuthClient.buid == app).one_or_404()

    @route('', methods=['GET'])
    @render_with('auth_client.html.jinja2')
    @requires_permission('view')
    def view(self):
        if self.obj.user:
            permassignments = AuthClientUserPermissions.all_forclient(self.obj).all()
        else:
            permassignments = AuthClientTeamPermissions.all_forclient(self.obj).all()
        return {'auth_client': self.obj, 'permassignments': permassignments}

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('edit')
    def edit(self):
        form = AuthClientForm(obj=self.obj, model=AuthClient)
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
                        "This application’s owner has changed, so all previously"
                        " assigned permissions have been revoked"
                    ),
                    'warning',
                )
            form.populate_obj(self.obj)
            self.obj.user = form.user
            self.obj.organization = form.organization
            db.session.commit()
            return render_redirect(self.obj.url_for(), code=303)

        return render_form(
            form=form,
            title=_("Edit application"),
            formid='client_edit',
            submit=_("Save changes"),
            ajax=True,
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
    @requires_permission('delete')
    def delete(self):
        return render_delete_sqla(
            self.obj,
            db,
            title=_("Confirm delete"),
            message=_(
                "Delete application ‘{title}’? This will also delete all associated"
                " content including access tokens issued on behalf of users. This"
                " operation is permanent and cannot be undone."
            ).format(title=self.obj.title),
            success=_(
                "You have deleted application ‘{title}’ and all its associated"
                " resources and permission assignments"
            ).format(title=self.obj.title),
            next=url_for('client_list'),
        )

    @route('cred', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('edit')
    def cred_new(self):
        form = AuthClientCredentialForm()
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
            return render_redirect(self.obj.url_for(), code=303)
        return render_form(
            form=form,
            title=_("Assign permissions"),
            message=Markup(
                _(
                    'Add and edit teams from <a href="{url}">your organization’s teams'
                    ' page</a>.'
                ).format(url=self.obj.organization.url_for('teams'))
            )
            if self.obj.organization
            else None,
            formid='perm_assign',
            submit=_("Assign permissions"),
        )


AuthClientView.init_app(app)

# --- Routes: client credentials ----------------------------------------------


@AuthClientCredential.views('main')
@route('/apps/info/<app>/cred/<name>')
class AuthClientCredentialView(UrlForView, ModelView):
    model = AuthClientCredential
    route_model_map = {'app': 'auth_client.buid', 'name': 'name'}

    def loader(self, app, name):
        cred = (
            self.model.query.join(AuthClient)
            .filter(AuthClient.buid == app, AuthClientCredential.name == name)
            .first_or_404()
        )
        return cred

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
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
            next=self.obj.auth_client.url_for(),
        )


AuthClientCredentialView.init_app(app)


# --- Routes: client app permissions ------------------------------------------


@AuthClientUserPermissions.views('main')
@route('/apps/info/<app>/perms/u/<user>')
class AuthClientUserPermissionsView(UrlForView, ModelView):
    model = AuthClientUserPermissions
    route_model_map = {'app': 'auth_client.buid', 'user': 'user.buid'}

    def loader(self, app, user):
        user = User.get(buid=user)
        perm = (
            self.model.query.join(AuthClient)
            .filter(AuthClient.buid == app, self.model.user == user)
            .one_or_404()
        )
        return perm

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('assign-permissions')
    def edit(self):
        form = AuthClientPermissionEditForm()
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
            return render_redirect(self.obj.auth_client.url_for(), code=303)
        return render_form(
            form=form,
            title=_("Edit permissions"),
            formid='perm_edit',
            submit=_("Save changes"),
            ajax=True,
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
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
            next=self.obj.auth_client.url_for(),
        )


AuthClientUserPermissionsView.init_app(app)


@AuthClientTeamPermissions.views('main')
@route('/apps/info/<app>/perms/t/<team>')
class AuthClientTeamPermissionsView(UrlForView, ModelView):
    model = AuthClientTeamPermissions
    route_model_map = {'app': 'auth_client.buid', 'team': 'team.buid'}

    def loader(self, app, team):
        team = Team.get(buid=team)
        perm = (
            self.model.query.join(AuthClient)
            .filter(AuthClient.buid == app, self.model.team == team)
            .one_or_404()
        )
        return perm

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @requires_permission('assign-permissions')
    def edit(self):
        form = AuthClientPermissionEditForm()
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
            return render_redirect(self.obj.auth_client.url_for(), code=303)
        return render_form(
            form=form,
            title=_("Edit permissions"),
            formid='perm_edit',
            submit=_("Save changes"),
            ajax=True,
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
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
            next=self.obj.auth_client.url_for(),
        )


AuthClientTeamPermissionsView.init_app(app)
