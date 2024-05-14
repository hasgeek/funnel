"""Views for organization admin and project crew membership management."""

from __future__ import annotations

from flask import abort, flash, request

from baseframe import _
from baseframe.forms import Form, render_form
from coaster.sqlalchemy import RoleAccessProxy
from coaster.views import (
    ModelView,
    UrlChangeCheck,
    UrlForView,
    render_with,
    requires_roles,
    route,
)

from .. import app, signals
from ..auth import current_auth
from ..forms import (
    OrganizationMembershipForm,
    ProjectCrewMembershipForm,
    ProjectCrewMembershipInviteForm,
)
from ..models import (
    Account,
    AccountAdminNotification,
    AccountAdminRevokedNotification,
    AccountMembership,
    MembershipRevokedError,
    Project,
    ProjectCrewNotification,
    ProjectCrewRevokedNotification,
    ProjectMembership,
    User,
    db,
)
from ..proxies import request_wants
from ..typing import ReturnRenderWith, ReturnView
from .helpers import LayoutTemplate, html_in_json, render_redirect
from .login_session import requires_login, requires_sudo
from .mixins import AccountCheckMixin, AccountViewBase, ProjectViewBase
from .notification import dispatch_notification

# MARK: Templates ----------------------------------------------------------------------


class MembershipInviteActionsTemplate(
    LayoutTemplate, template='membership_invite_actions.html.jinja2'
):
    membership: ProjectMembership | RoleAccessProxy[ProjectMembership]
    form: Form


# MARK: Views --------------------------------------------------------------------------


@Account.views('members')
@route('/<account>/members', init_app=app)
class OrganizationMembersView(AccountViewBase):

    def after_loader(self) -> ReturnView | None:
        """Don't render member views for user accounts."""
        if isinstance(self.obj, User):
            # Only non-user accounts have admin/owner members
            abort(404)
        return super().after_loader()

    @route('', methods=['GET', 'POST'])
    @render_with('account_admins.html.jinja2')
    @requires_roles({'reader', 'admin'})
    def members(self) -> ReturnRenderWith:
        """Render a list of organization admin members."""
        return {
            'profile': self.obj,  # FIXME: Upgrade templates
            'account': self.obj,
            'memberships': [
                membership.current_access(datasets=('without_parent', 'related'))
                for membership in self.obj.active_admin_memberships
            ],
        }

    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'owner'})
    def new_member(self) -> ReturnView:
        membership_form = OrganizationMembershipForm()

        if request.method == 'POST':
            if membership_form.validate_on_submit():
                if not membership_form.user.data.has_verified_contact_info:
                    # users without verified contact information cannot be members
                    return {
                        'status': 'error',
                        'error_description': _(
                            "This user does not have any verified contact"
                            " information. If you are able to contact them, please"
                            " ask them to verify their email address or phone"
                            " number"
                        ),
                        'errors': membership_form.errors,
                    }, 422

                previous_membership = (
                    AccountMembership.query.filter(AccountMembership.is_active)
                    .filter_by(
                        account=self.obj,
                        member=membership_form.user.data,
                    )
                    .one_or_none()
                )
                if previous_membership is not None:
                    return {
                        'status': 'error',
                        'error_description': _("This user is already an admin"),
                        'errors': membership_form.errors,
                    }, 422

                new_membership = AccountMembership(
                    account=self.obj, granted_by=current_auth.user, is_admin=True
                )
                membership_form.populate_obj(new_membership)
                db.session.add(new_membership)
                db.session.commit()
                dispatch_notification(
                    AccountAdminNotification(
                        document=new_membership.account,
                        fragment=new_membership,
                    )
                )
                return {
                    'status': 'ok',
                    'message': _("The user has been added as an admin"),
                    'memberships': [
                        membership.current_access(
                            datasets=('without_parent', 'related')
                        )
                        for membership in self.obj.active_admin_memberships
                    ],
                }, 201
            return {
                'status': 'error',
                'error_description': _("The new admin could not be added"),
                'errors': membership_form.errors,
            }, 422

        membership_form_html = render_form(
            form=membership_form,
            title='',
            submit='Add member',
            ajax=False,
            with_chrome=False,
        ).get_data(as_text=True)
        return {'status': 'ok', 'form': membership_form_html}


@AccountMembership.views('main')
@route('/<account>/members/<membership>', init_app=app)
class OrganizationMembershipView(
    AccountCheckMixin, UrlChangeCheck, UrlForView, ModelView[AccountMembership]
):
    route_model_map = {'account': 'account.urlname', 'membership': 'uuid_b58'}

    def load(self, account: str, membership: str) -> ReturnView | None:
        self.obj = AccountMembership.query.filter(
            AccountMembership.uuid_b58 == membership,
        ).first_or_404()
        if not self.obj.is_active:
            abort(410)
        return self.after_loader()

    @property
    def account(self) -> Account:
        return self.obj.account

    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'account_owner'})
    def edit(self) -> ReturnView:
        previous_membership = self.obj
        membership_form = OrganizationMembershipForm(obj=previous_membership)

        if request.method == 'POST':
            if membership_form.validate_on_submit():
                if previous_membership.member == current_auth.user:
                    return {
                        'status': 'error',
                        'error_description': _("You can’t edit your own role"),
                    }, 422

                try:
                    new_membership = previous_membership.replace(
                        actor=current_auth.user,
                        is_owner=membership_form.is_owner.data,
                        is_admin=True,
                    )
                except MembershipRevokedError:
                    return {
                        'status': 'error',
                        'error_description': _(
                            "This member’s record was edited elsewhere."
                            " Reload the page"
                        ),
                    }, 422
                if new_membership != previous_membership:
                    db.session.commit()
                    dispatch_notification(
                        AccountAdminNotification(
                            document=new_membership.account,
                            fragment=new_membership,
                        )
                    )
                return {
                    'status': 'ok',
                    'message': (
                        _("The member’s roles have been updated")
                        if new_membership != previous_membership
                        else _("No changes were detected")
                    ),
                    'memberships': [
                        membership.current_access(
                            datasets=('without_parent', 'related')
                        )
                        for membership in self.obj.account.active_admin_memberships
                    ],
                }
            return {
                'status': 'error',
                'error_description': _("Please pick one or more roles"),
                'errors': membership_form.errors,
            }, 422

        membership_form_html = render_form(
            form=membership_form,
            title='',
            submit='Edit membership',
            ajax=False,
            with_chrome=False,
        ).get_data(as_text=True)
        return {'status': 'ok', 'form': membership_form_html}

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
    @requires_roles({'account_owner'})
    def delete(self) -> ReturnView:
        form = Form()
        if form.is_submitted():
            if form.validate():
                previous_membership = self.obj
                if previous_membership.member == current_auth.user:
                    return {
                        'status': 'error',
                        'error_description': _("You can’t revoke your own membership"),
                    }, 422
                if not previous_membership.is_admin:
                    return {
                        'status': 'error',
                        'error_description': _("This person is not an admin"),
                    }, 422
                previous_membership.revoke_member(current_auth.user)
                db.session.commit()
                dispatch_notification(
                    AccountAdminRevokedNotification(
                        document=previous_membership.account,
                        fragment=previous_membership,
                    )
                )
                return {
                    'status': 'ok',
                    'message': _("The admin has been removed"),
                    'memberships': [
                        membership.current_access(
                            datasets=('without_parent', 'related')
                        )
                        for membership in self.obj.account.active_admin_memberships
                    ],
                }
            return {
                'status': 'error',
                'errors': form.errors,
            }, 422

        form_html = render_form(
            form=form,
            title=_("Confirm removal"),
            message=_("Remove {member} as an admin from {account}?").format(
                member=self.obj.member.fullname, account=self.obj.account.title
            ),
            submit=_("Remove"),
            ajax=False,
            with_chrome=False,
        ).get_data(as_text=True)
        return {'status': 'ok', 'form': form_html}


#: Project Membership views


@Project.views('crew')
@route('/<account>/<project>/crew', init_app=app)
class ProjectCrewView(ProjectViewBase):
    @route('', methods=['GET', 'POST'])
    @render_with(html_in_json('project_membership.html.jinja2'))
    def crew(self) -> ReturnRenderWith:
        memberships = [
            membership.current_access(datasets=('without_parent', 'related'))
            for membership in self.obj.active_crew_memberships
        ]
        return {
            'project': self.obj.current_access(datasets=('primary', 'related')),
            'memberships': memberships,
        }

    @route('new', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'account_admin'})
    def new_member(self) -> ReturnView:
        membership_form = ProjectCrewMembershipForm()

        if request.method == 'POST':
            if membership_form.validate_on_submit():
                if not membership_form.user.data.has_verified_contact_info:
                    # users without verified contact information cannot be members
                    return {
                        'status': 'error',
                        'error_description': _(
                            "This user does not have any verified contact information."
                            " If you are able to contact them, please ask them to"
                            " verify their email address or phone number"
                        ),
                        'errors': membership_form.errors,
                    }, 422
                previous_membership = (
                    ProjectMembership.query.filter(ProjectMembership.is_active)
                    .filter_by(project=self.obj, member=membership_form.user.data)
                    .one_or_none()
                )
                if previous_membership is not None:
                    return {
                        'status': 'error',
                        'error_description': _("This person is already a member"),
                        'errors': membership_form.errors,
                    }, 422
                new_membership = ProjectMembership(
                    project=self.obj, granted_by=current_auth.user
                )
                membership_form.populate_obj(new_membership)
                db.session.add(new_membership)
                db.session.commit()
                signals.project_role_change.send(
                    self.obj, actor=current_auth.user, user=new_membership.member
                )
                dispatch_notification(
                    ProjectCrewNotification(document=self.obj, fragment=new_membership)
                )
                return {
                    'status': 'ok',
                    'message': _("The user has been added as a member"),
                    'memberships': [
                        membership.current_access(
                            datasets=('without_parent', 'related')
                        )
                        for membership in self.obj.active_crew_memberships
                    ],
                }, 201
            return {
                'status': 'error',
                'error_description': _("Please pick one or more roles"),
                'errors': membership_form.errors,
            }, 422

        membership_form_html = render_form(
            form=membership_form,
            title='',
            submit='Add member',
            ajax=False,
            with_chrome=False,
        ).get_data(as_text=True)
        return {'status': 'ok', 'form': membership_form_html}


class ProjectMembershipViewBase(
    AccountCheckMixin, UrlChangeCheck, UrlForView, ModelView[ProjectMembership]
):
    route_model_map = {
        'account': 'project.account.urlname',
        'project': 'project.name',
        'membership': 'uuid_b58',
    }

    def load(self, account: str, project: str, membership: str) -> ReturnView | None:
        self.obj = (
            ProjectMembership.query.join(Project)
            .join(Account, Project.account)
            .filter(
                Account.name_is(account),
                Project.name == project,
                ProjectMembership.uuid_b58 == membership,
            )
            .first_or_404()
        )
        return self.after_loader()

    @property
    def account(self) -> Account:
        return self.obj.project.account


@ProjectMembership.views('invite')
@route('/<account>/<project>/crew/<membership>/invite', init_app=app)
class ProjectMembershipInviteView(ProjectMembershipViewBase):
    def load(self, account: str, project: str, membership: str) -> ReturnView | None:
        resp = super().load(account, project, membership)
        if not self.obj.is_invite or self.obj.member != current_auth.user:
            abort(404)
        return resp

    @route('', methods=['GET'])
    @requires_login
    @requires_roles({'member'})
    def invite(self) -> ReturnView:
        status_code = 200
        if request.method == 'GET':
            return MembershipInviteActionsTemplate(
                membership=self.obj.current_access(datasets=('primary', 'related')),
                form=Form(),
            ).render_template()
        membership_invite_form = ProjectCrewMembershipInviteForm()
        if membership_invite_form.validate_on_submit():
            if membership_invite_form.action.data == 'accept':
                self.obj.accept(actor=current_auth.user)
                status_code = 201
            elif membership_invite_form.action.data == 'decline':
                self.obj.revoke(actor=current_auth.user)
            else:
                error_description = _("This is not a valid response")
                if request_wants.json:
                    return {
                        'status': 'error',
                        'error': 'invalid_action',
                        'error_description': error_description,
                    }, 422
                flash(error_description, 'error')
                abort(422)
            db.session.commit()
        if request_wants.json:
            return {
                'status': 'ok',
                'action': membership_invite_form.action.data,
            }, status_code
        return render_redirect(self.obj.project.url_for())


@ProjectMembership.views('main')
@route('/<account>/<project>/crew/<membership>', init_app=app)
class ProjectMembershipView(ProjectMembershipViewBase):
    @route('edit', methods=['GET', 'POST'])
    @requires_login
    @requires_roles({'account_admin'})
    def edit(self) -> ReturnView:
        previous_membership = self.obj
        form = ProjectCrewMembershipForm(obj=previous_membership)

        if form.is_submitted():
            if form.validate():
                try:
                    new_membership = previous_membership.replace(
                        actor=current_auth.user,
                        is_editor=form.is_editor.data,
                        is_promoter=form.is_promoter.data,
                        is_usher=form.is_usher.data,
                        label=form.label.data,
                    )
                except MembershipRevokedError:
                    return {
                        'status': 'error',
                        'error_description': _(
                            "The member’s record was edited elsewhere."
                            " Reload the page"
                        ),
                    }, 422
                if new_membership != previous_membership:
                    db.session.commit()
                    signals.project_role_change.send(
                        self.obj.project, actor=current_auth.user, user=self.obj.member
                    )
                    dispatch_notification(
                        ProjectCrewNotification(
                            document=self.obj.project, fragment=new_membership
                        )
                    )
                return {
                    'status': 'ok',
                    'message': _("The member’s roles have been updated"),
                    'memberships': [
                        membership.current_access(
                            datasets=('without_parent', 'related')
                        )
                        for membership in self.obj.project.active_crew_memberships
                    ],
                }
            return {
                'status': 'error',
                'error_description': _("Please pick one or more roles"),
                'errors': form.errors,
            }, 422

        membership_form_html = render_form(
            form=form,
            title='',
            submit='Edit membership',
            ajax=False,
            with_chrome=False,
        ).get_data(as_text=True)
        return {'status': 'ok', 'form': membership_form_html}

    @route('delete', methods=['GET', 'POST'])
    @requires_sudo
    @requires_roles({'account_admin'})
    def delete(self) -> ReturnView:
        form = Form()
        if request.method == 'POST':
            if form.validate():
                previous_membership = self.obj
                if previous_membership.is_active:
                    previous_membership.revoke(actor=current_auth.user)
                    db.session.commit()
                    signals.project_role_change.send(
                        self.obj.project, actor=current_auth.user, user=self.obj.member
                    )
                    dispatch_notification(
                        ProjectCrewRevokedNotification(
                            document=previous_membership.project,
                            fragment=previous_membership,
                        )
                    )
                return {
                    'status': 'ok',
                    'message': _("The member has been removed"),
                    'memberships': [
                        membership.current_access(
                            datasets=('without_parent', 'related')
                        )
                        for membership in self.obj.project.active_crew_memberships
                    ],
                }
            return {'status': 'error', 'errors': form.errors}, 422

        form_html = render_form(
            form=form,
            title=_("Confirm removal"),
            message=_("Remove {member} as a crew member from this project?").format(
                member=self.obj.member.fullname
            ),
            submit=_("Remove"),
            ajax=False,
            with_chrome=False,
        ).get_data(as_text=True)
        return {'status': 'ok', 'form': form_html}
