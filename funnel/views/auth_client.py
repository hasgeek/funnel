"""Views to browse and manage client auth apps."""

from __future__ import annotations

from collections.abc import Iterable

from flask import flash, request, url_for

from baseframe import _
from baseframe.forms import render_delete_sqla, render_form
from coaster.views import (
    ClassView,
    ModelView,
    UrlForView,
    render_with,
    requires_roles,
    route,
)

from .. import app
from ..auth import current_auth
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
    AuthClientPermissions,
    AuthClientTeamPermissions,
    Team,
    db,
)
from ..typing import ReturnRenderWith, ReturnView
from .helpers import LayoutTemplate, render_redirect
from .login_session import requires_login, requires_sudo

# MARK: Templates ----------------------------------------------------------------------


class AuthClientIndexTemplate(LayoutTemplate, template='auth_client_index.html.jinja2'):
    auth_clients: Iterable[AuthClient]


class AuthClientCredentialTemplate(
    LayoutTemplate, template='auth_client_credential.html.jinja2'
):
    name: str
    secret: str
    cred: AuthClientCredential


# MARK: Routes: client apps ------------------------------------------------------------


@app.route('/apps')
@requires_login
def client_list() -> ReturnView:
    return AuthClientIndexTemplate(
        auth_clients=AuthClient.all_for(current_auth.user),
    ).render_template()


@app.route('/apps/all')
def client_list_all() -> ReturnView:
    return AuthClientIndexTemplate(
        auth_clients=AuthClient.all_for(None)
    ).render_template()


def available_client_owners() -> list[tuple[str, str]]:
    """Return a list of possible client owners for the current user."""
    choices = []
    choices.append((current_auth.user.buid, current_auth.user.pickername))
    choices.extend(
        (org.buid, org.pickername) for org in current_auth.user.organizations_as_owner
    )
    return choices


@route('/apps/new', methods=['GET', 'POST'], init_app=app)
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


@AuthClient.views('main')
@route('/apps/info/<client>', init_app=app)
class AuthClientView(UrlForView, ModelView[AuthClient]):
    route_model_map = {'client': 'buid'}

    def loader(self, client: str) -> AuthClient:
        return AuthClient.query.filter(AuthClient.buid == client).one_or_404()

    @route('', methods=['GET'])
    @render_with('auth_client.html.jinja2')
    @requires_roles({'all'})
    def view(self) -> ReturnRenderWith:
        permassignments = AuthClientPermissions.all_forclient(self.obj).all()
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
                AuthClientPermissions.all_forclient(self.obj).delete(
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
            return AuthClientCredentialTemplate(
                name=cred.name,
                secret=secret,
                cred=cred,
            ).render_template()
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
            permassign = AuthClientPermissions.get(
                auth_client=self.obj, account=form.user.data
            )
            if permassign is not None:
                perms.update(permassign.access_permissions.split())
            else:
                permassign = AuthClientPermissions(
                    account=form.user.data, auth_client=self.obj
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


# MARK: Routes: client credentials -----------------------------------------------------


@AuthClientCredential.views('main')
@route('/apps/info/<client>/cred/<name>', init_app=app)
class AuthClientCredentialView(UrlForView, ModelView[AuthClientCredential]):
    route_model_map = {'client': 'auth_client.buid', 'name': 'name'}

    def loader(self, client: str, name: str) -> AuthClientCredential:
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


# MARK: Routes: client app permissions -------------------------------------------------


@AuthClientPermissions.views('main')
@route('/apps/info/<client>/perms/u/<account>', init_app=app)
class AuthClientPermissionsView(UrlForView, ModelView[AuthClientPermissions]):
    route_model_map = {'client': 'auth_client.buid', 'account': 'account.buid'}

    def loader(self, client: str, account: str) -> AuthClientPermissions:
        return (
            AuthClientPermissions.query.join(
                AuthClient, AuthClientPermissions.auth_client
            )
            .join(Account, AuthClientPermissions.account)
            .filter(AuthClient.buid == client, Account.buid == account)
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
                        pname=self.obj.account.pickername
                    ),
                    'success',
                )
            else:
                flash(
                    _("All permissions have been revoked for user {pname}").format(
                        pname=self.obj.account.pickername
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
            ).format(
                pname=self.obj.account.pickername, title=self.obj.auth_client.title
            ),
            success=_("You have revoked permissions for user {pname}").format(
                pname=self.obj.account.pickername
            ),
            next=self.obj.auth_client.url_for(),
        )


@AuthClientTeamPermissions.views('main')
@route('/apps/info/<client>/perms/t/<team>', init_app=app)
class AuthClientTeamPermissionsView(UrlForView, ModelView[AuthClientTeamPermissions]):
    route_model_map = {'client': 'auth_client.buid', 'team': 'team.buid'}

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
            success=_("You have revoked permissions for team {title}").format(
                title=self.obj.team.title
            ),
            next=self.obj.auth_client.url_for(),
        )
