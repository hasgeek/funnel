"""Views for organization admin and project crew membership management."""

from __future__ import annotations

from typing import Optional

from flask import abort, flash, render_template, request

from baseframe import _
from baseframe.forms import Form, render_form
from coaster.auth import current_auth
from coaster.views import (
    ModelView,
    UrlChangeCheck,
    UrlForView,
    render_with,
    requires_roles,
    route,
)

from .. import app, signals
from ..forms import (
    OrganizationMembershipForm,
    ProjectCrewMembershipForm,
    ProjectCrewMembershipInviteForm,
)
from ..models import (
    Account,
    AccountAdminMembership,
    MembershipRevokedError,
    Organization,
    OrganizationAdminMembershipNotification,
    OrganizationAdminMembershipRevokedNotification,
    Project,
    ProjectCrewMembership,
    ProjectCrewMembershipNotification,
    ProjectCrewMembershipRevokedNotification,
    db,
)
from ..proxies import request_wants
from ..typing import ReturnRenderWith, ReturnView
from .helpers import html_in_json, render_redirect
from .login_session import requires_login, requires_sudo
from .mixins import AccountCheckMixin, AccountViewMixin, ProjectViewMixin
from .notification import dispatch_notification


@Account.views('members')
@route('/<account>/members')
class OrganizationMembersView(AccountViewMixin, UrlForView, ModelView):
    def after_loader(self) -> Optional[ReturnView]:  # type: ignore[return]
        """Don't render member views for user accounts."""
        if not isinstance(self.obj, Organization):
            # Only organization accounts have admin members
            abort(404)

    @route('', methods=['GET', 'POST'])
    @render_with('organization_membership.html.jinja2')
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
                    return (
                        {
                            'status': 'error',
                            'error_description': _(
                                "This user does not have any verified contact"
                                " information. If you are able to contact them, please"
                                " ask them to verify their email address or phone"
                                " number"
                            ),
                            'errors': membership_form.errors,
                            'form_nonce': membership_form.form_nonce.data,
                        },
                        422,
                    )

                previous_membership = (
                    AccountAdminMembership.query.filter(
                        AccountAdminMembership.is_active
                    )
                    .filter_by(
                        account=self.obj,
                        member=membership_form.user.data,
                    )
                    .one_or_none()
                )
                if previous_membership is not None:
                    return (
                        {
                            'status': 'error',
                            'error_description': _("This user is already an admin"),
                            'errors': membership_form.errors,
                            'form_nonce': membership_form.form_nonce.data,
                        },
                        422,
                    )
                new_membership = AccountAdminMembership(
                    account=self.obj, granted_by=current_auth.user
                )
                membership_form.populate_obj(new_membership)
                db.session.add(new_membership)
                db.session.commit()
                dispatch_notification(
                    OrganizationAdminMembershipNotification(
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
            return (
                {
                    'status': 'error',
                    'error_description': _("The new admin could not be added"),
                    'errors': membership_form.errors,
                    'form_nonce': membership_form.form_nonce.data,
                },
                422,
            )

        membership_form_html = render_form(
            form=membership_form,
            title='',
            submit='Add member',
            ajax=False,
            with_chrome=False,
        ).get_data(as_text=True)
        return {'status': 'ok', 'form': membership_form_html}


OrganizationMembersView.init_app(app)


@AccountAdminMembership.views('main')
@route('/<account>/members/<membership>')
class OrganizationMembershipView(
    AccountCheckMixin, UrlChangeCheck, UrlForView, ModelView
):
    model = AccountAdminMembership
    route_model_map = {'account': 'account.name', 'membership': 'uuid_b58'}
    obj: AccountAdminMembership

    def loader(self, account, membership) -> AccountAdminMembership:
        return AccountAdminMembership.query.filter(
            AccountAdminMembership.uuid_b58 == membership,
        ).first_or_404()

    def after_loader(self) -> Optional[ReturnView]:
        self.account = self.obj.account
        return super().after_loader()

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
                        'form_nonce': membership_form.form_nonce.data,
                    }, 422

                try:
                    new_membership = previous_membership.replace(
                        actor=current_auth.user, is_owner=membership_form.is_owner.data
                    )
                except MembershipRevokedError:
                    return {
                        'status': 'error',
                        'error_description': _(
                            "This member’s record was edited elsewhere."
                            " Reload the page"
                        ),
                        'form_nonce': membership_form.form_nonce.data,
                    }, 422
                if new_membership != previous_membership:
                    db.session.commit()
                    dispatch_notification(
                        OrganizationAdminMembershipNotification(
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
                'form_nonce': membership_form.form_nonce.data,
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
                        'form_nonce': form.form_nonce.data,
                    }, 422
                if previous_membership.is_active:
                    previous_membership.revoke(actor=current_auth.user)
                    db.session.commit()
                    dispatch_notification(
                        OrganizationAdminMembershipRevokedNotification(
                            document=previous_membership.account,
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
                        for membership in self.obj.account.active_admin_memberships
                    ],
                }
            return {
                'status': 'error',
                'errors': form.errors,
                'form_nonce': form.form_nonce.data,
            }, 422

        form_html = render_form(
            form=form,
            title=_("Confirm removal"),
            message=_("Remove {member} as an admin from {account}?").format(
                member=self.obj.user.fullname, account=self.obj.account.title
            ),
            submit=_("Remove"),
            ajax=False,
            with_chrome=False,
        ).get_data(as_text=True)
        return {'status': 'ok', 'form': form_html}


OrganizationMembershipView.init_app(app)


#: Project Membership views


@Project.views('crew')
@route('/<account>/<project>/crew')
class ProjectMembershipView(ProjectViewMixin, UrlChangeCheck, UrlForView, ModelView):
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
                        'form_nonce': membership_form.form_nonce.data,
                    }, 422
                previous_membership = (
                    ProjectCrewMembership.query.filter(ProjectCrewMembership.is_active)
                    .filter_by(project=self.obj, member=membership_form.user.data)
                    .one_or_none()
                )
                if previous_membership is not None:
                    return {
                        'status': 'error',
                        'error_description': _("This person is already a member"),
                        'errors': membership_form.errors,
                        'form_nonce': membership_form.form_nonce.data,
                    }, 422
                new_membership = ProjectCrewMembership(
                    project=self.obj, granted_by=current_auth.user
                )
                membership_form.populate_obj(new_membership)
                db.session.add(new_membership)
                db.session.commit()
                signals.project_role_change.send(
                    self.obj, actor=current_auth.user, user=new_membership.member
                )
                dispatch_notification(
                    ProjectCrewMembershipNotification(
                        document=self.obj, fragment=new_membership
                    )
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
                'form_nonce': membership_form.form_nonce.data,
            }, 422

        membership_form_html = render_form(
            form=membership_form,
            title='',
            submit='Add member',
            ajax=False,
            with_chrome=False,
        ).get_data(as_text=True)
        return {'status': 'ok', 'form': membership_form_html}


ProjectMembershipView.init_app(app)


class ProjectCrewMembershipMixin(AccountCheckMixin):
    model = ProjectCrewMembership
    route_model_map = {
        'account': 'project.account.name',
        'project': 'project.name',
        'membership': 'uuid_b58',
    }
    obj: ProjectCrewMembership

    def loader(self, account, project, membership) -> ProjectCrewMembership:
        return (
            ProjectCrewMembership.query.join(Project)
            .join(Account, Project.account)
            .filter(
                Account.name_is(account),
                Project.name == project,
                ProjectCrewMembership.uuid_b58 == membership,
            )
            .first_or_404()
        )

    def after_loader(self) -> Optional[ReturnView]:
        self.account = self.obj.project.account
        return super().after_loader()


@ProjectCrewMembership.views('invite')
@route('/<account>/<project>/crew/<membership>/invite')
class ProjectCrewMembershipInviteView(
    ProjectCrewMembershipMixin, UrlChangeCheck, UrlForView, ModelView
):
    def loader(self, account, project, membership) -> ProjectCrewMembership:
        obj = super().loader(account, project, membership)
        if not obj.is_invite or obj.user != current_auth.user:
            abort(404)
        return obj

    @route('', methods=['GET'])
    @requires_login
    @requires_roles({'member'})
    def invite(self) -> ReturnView:
        if request.method == 'GET':
            return render_template(
                'membership_invite_actions.html.jinja2',
                membership=self.obj.current_access(datasets=('primary', 'related')),
                form=Form(),
            )
        membership_invite_form = ProjectCrewMembershipInviteForm()
        if membership_invite_form.validate_on_submit():
            if membership_invite_form.action.data == 'accept':
                self.obj.accept(actor=current_auth.user)
                status_code = 201
            elif membership_invite_form.action.data == 'decline':
                self.obj.revoke(actor=current_auth.user)
                status_code = 200
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


ProjectCrewMembershipInviteView.init_app(app)


@ProjectCrewMembership.views('main')
@route('/<account>/<project>/crew/<membership>')
class ProjectCrewMembershipView(
    ProjectCrewMembershipMixin, UrlChangeCheck, UrlForView, ModelView
):
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
                        'form_nonce': form.form_nonce.data,
                    }, 422
                if new_membership != previous_membership:
                    db.session.commit()
                    signals.project_role_change.send(
                        self.obj.project, actor=current_auth.user, user=self.obj.user
                    )
                    dispatch_notification(
                        ProjectCrewMembershipNotification(
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
                'form_nonce': form.form_nonce.data,
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
                        self.obj.project, actor=current_auth.user, user=self.obj.user
                    )
                    dispatch_notification(
                        ProjectCrewMembershipRevokedNotification(
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
                member=self.obj.user.fullname
            ),
            submit=_("Remove"),
            ajax=False,
            with_chrome=False,
        ).get_data(as_text=True)
        return {'status': 'ok', 'form': form_html}


ProjectCrewMembershipView.init_app(app)
