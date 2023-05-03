"""Views to browse and manage client auth apps."""

from __future__ import annotations

from typing import List, Tuple
from uuid import UUID  # noqa: F401 # pylint: disable=unused-import

from flask import flash, render_template, request, url_for

from baseframe import _
from baseframe.forms import render_delete_sqla, render_form
from coaster.auth import current_auth
from coaster.views import (
    ClassView,
    ModelView,
    UrlForView,
    render_with,
    requires_roles,
    route,
)

from .. import app
from ..forms import (
    AuthClientCredentialForm,
    AuthClientForm,
    AuthClientPermissionEditForm,
    UserPermissionAssignForm,
)
from ..models import (
    Account,
    AuthClient,
    AuthClientCredential,
    AuthClientTeamPermissions,
    AuthClientUserPermissions,
    Team,
    db,
)
from ..typing import ReturnRenderWith, ReturnView
from .helpers import render_redirect
from .login_session import requires_login, requires_sudo

# --- Routes: client apps -----------------------------------------------------


@app.route('/apps')
@requires_login
def client_list() -> ReturnView:
    return render_template(
        'auth_client_index.html.jinja2',
        auth_clients=AuthClient.all_for(current_auth.user),
    )


@app.route('/apps/all')
def client_list_all() -> ReturnView:
    return render_template(
        'auth_client_index.html.jinja2', auth_clients=AuthClient.all_for(None)
    )


def available_client_owners() -> List[Tuple[str, str]]:
    """Return a list of possible client owners for the current user."""
    choices = []
    choices.append((current_auth.user.buid, current_auth.user.pickername))
    for org in current_auth.user.organizations_as_owner:
        choices.append((org.buid, org.pickername))
    return choices


@route('/apps/new', methods=['GET', 'POST'])
class AuthClientCreateView(ClassView):
    @route('', endpoint='authclient_new')
    @requires_login
    def new(self) -> ReturnView:
        form = AuthClientForm(model=AuthClient)
        form.edit_user = current_auth.user
        form.client_owner.choices = available_client_owners()
        if request.method == 'GET':
            form.client_owner.data = current_auth.user.buid

        if form.validate_on_submit():
            auth_client = AuthClient()
            form.populate_obj(auth_client)
            auth_client.account = form.account
            auth_client.trusted = False
            db.session.add(auth_client)
            db.session.commit()
            return render_redirect(auth_client.url_for())

        return render_form(
            form=form,
            title=_("Register a new client application"),
            formid='client_new',
            submit=_("Register application"),
            ajax=True,
        )


AuthClientCreateView.init_app(app)


@AuthClient.views('main')
@route('/apps/info/<client>')
class AuthClientView(UrlForView, ModelView):
    model = AuthClient
    route_model_map = {'client': 'buid'}
    obj: AuthClient

    def loader(self, client) -> AuthClient:
        return AuthClient.query.filter(AuthClient.buid == client).one_or_404()

    @route('', methods=['GET'])
    @render_with('auth_client.html.jinja2')
    @requires_roles({'all'})
    def view(self) -> ReturnRenderWith:
        permassignments = AuthClientUserPermissions.all_forclient(self.obj).all()
        return {'auth_client': self.obj, 'permassignments': permassignments}

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'owner'})
    def edit(self) -> ReturnView:
        form = AuthClientForm(obj=self.obj, model=AuthClient)
        form.edit_user = current_auth.user
        form.client_owner.choices = available_client_owners()
        if request.method == 'GET':
            form.client_owner.data = self.obj.account.buid

        if form.validate_on_submit():
            if self.obj.account != form.account:
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
            self.obj.account = form.account
            db.session.commit()
            return render_redirect(self.obj.url_for())

        return render_form(
            form=form,
            title=_("Edit application"),
            formid='client_edit',
            submit=_("Save changes"),
            ajax=True,
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
    @requires_roles({'owner'})
    def delete(self) -> ReturnView:
        return render_delete_sqla(
            self.obj,
            db,
            title=_("Confirm delete"),
            message=_(
                "Delete application ‘{title}’? This will also delete all associated"
                " content including access tokens issued on behalf of users. This"
                " operation is permanent and cannot be undone"
            ).format(title=self.obj.title),
            success=_(
                "You have deleted application ‘{title}’ and all its associated"
                " resources and permission assignments"
            ).format(title=self.obj.title),
            next=url_for('client_list'),
        )

    @route('disconnect', methods=['GET', 'POST'])
    @requires_sudo
    def disconnect(self) -> ReturnView:
        auth_token = self.obj.authtoken_for(current_auth.user)
        if auth_token is None:
            return render_redirect(self.obj.url_for())

        return render_delete_sqla(
            auth_token,
            db,
            title=_("Disconnect {app}").format(app=self.obj.title),
            message=_(
                "Disconnect application {app}? This will not remove any of your data in"
                " this app, but will prevent it from accessing any further data from"
                " your Hasgeek account"
            ).format(app=self.obj.title),
            delete_text=_("Disconnect"),
            success=_("You have disconnected {app} from your account").format(
                app=self.obj.title
            ),
            next=url_for('account'),
        )

    @route('cred', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'owner'})
    def cred_new(self) -> ReturnView:
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
    @requires_roles({'owner'})
    def permission_user_new(self) -> ReturnView:
        form = UserPermissionAssignForm()
        if form.validate_on_submit():
            perms = set()
            permassign = AuthClientUserPermissions.get(
                auth_client=self.obj, user=form.user.data
            )
            if permassign is not None:
                perms.update(permassign.access_permissions.split())
            else:
                permassign = AuthClientUserPermissions(
                    user=form.user.data, auth_client=self.obj
                )
                db.session.add(permassign)
            perms.update(form.perms.data.split())
            permassign.access_permissions = ' '.join(sorted(perms))
            db.session.commit()
            flash(
                _("Permissions have been assigned to user {pname}").format(
                    pname=form.user.data.pickername
                ),
                'success',
            )
            return render_redirect(self.obj.url_for())
        return render_form(
            form=form,
            title=_("Assign permissions"),
            formid='perm_assign',
            submit=_("Assign permissions"),
        )


AuthClientView.init_app(app)

# --- Routes: client credentials ----------------------------------------------


@AuthClientCredential.views('main')
@route('/apps/info/<client>/cred/<name>')
class AuthClientCredentialView(UrlForView, ModelView):
    model = AuthClientCredential
    route_model_map = {'client': 'auth_client.buid', 'name': 'name'}
    obj: AuthClientCredential

    def loader(self, client, name) -> AuthClientCredential:
        return (
            AuthClientCredential.query.join(AuthClient)
            .filter(AuthClient.buid == client, AuthClientCredential.name == name)
            .first_or_404()
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
    @requires_roles({'owner'})
    def delete(self) -> ReturnView:
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
@route('/apps/info/<client>/perms/u/<user>')
class AuthClientUserPermissionsView(UrlForView, ModelView):
    model = AuthClientUserPermissions
    route_model_map = {'client': 'auth_client.buid', 'user': 'user.buid'}
    obj: AuthClientUserPermissions

    def loader(self, client: str, user: str) -> AuthClientUserPermissions:
        return (
            AuthClientUserPermissions.query.join(
                AuthClient, AuthClientUserPermissions.auth_client_id == AuthClient.id
            )
            .join(Account, AuthClientUserPermissions.user_id == Account.id)
            .filter(AuthClient.buid == client, Account.buid == user)
            .one_or_404()
        )

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'owner'})
    def edit(self) -> ReturnView:
        form = AuthClientPermissionEditForm()
        if request.method == 'GET' and self.obj:
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
            return render_redirect(self.obj.auth_client.url_for())
        return render_form(
            form=form,
            title=_("Edit permissions"),
            formid='perm_edit',
            submit=_("Save changes"),
            ajax=True,
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
    @requires_roles({'owner'})
    def delete(self) -> ReturnView:
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
@route('/apps/info/<client>/perms/t/<team>')
class AuthClientTeamPermissionsView(UrlForView, ModelView):
    model = AuthClientTeamPermissions
    route_model_map = {'client': 'auth_client.buid', 'team': 'team.buid'}
    obj: AuthClientTeamPermissions

    def loader(self, client: str, team: str) -> AuthClientTeamPermissions:
        return (
            AuthClientTeamPermissions.query.join(
                AuthClient, AuthClientTeamPermissions.auth_client_id == AuthClient.id
            )
            .join(Team, AuthClientTeamPermissions.team_id == Team.id)
            .filter(AuthClient.buid == client, Team.buid == team)
            .one_or_404()
        )

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'owner'})
    def edit(self) -> ReturnView:
        form = AuthClientPermissionEditForm()
        if request.method == 'GET' and self.obj:
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
            return render_redirect(self.obj.auth_client.url_for())
        return render_form(
            form=form,
            title=_("Edit permissions"),
            formid='perm_edit',
            submit=_("Save changes"),
            ajax=True,
        )

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
    @requires_roles({'owner'})
    def delete(self) -> ReturnView:
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
