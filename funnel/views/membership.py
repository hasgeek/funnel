from __future__ import annotations

from typing import Optional

from flask import abort, redirect, request

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
    MembershipRevokedError,
    OrganizationAdminMembershipNotification,
    OrganizationAdminMembershipRevokedNotification,
    OrganizationMembership,
    Profile,
    Project,
    ProjectCrewMembership,
    db,
)
from ..typing import ReturnView
from .login_session import requires_login, requires_sudo
from .mixins import ProfileCheckMixin, ProfileViewMixin, ProjectViewMixin
from .notification import dispatch_notification


@Profile.views('members')
@route('/<profile>/members')
class OrganizationMembersView(ProfileViewMixin, UrlForView, ModelView):
    def after_loader(self) -> Optional[ReturnView]:
        """Don't render member views for user profiles."""
        if not self.obj.organization:
            # User profiles don't have memberships
            abort(404)
        return None

    @route('', methods=['GET', 'POST'])
    @render_with('organization_membership.html.jinja2')
    @requires_roles({'reader', 'admin'})
    def members(self):
        """Render a list of organization admin members."""
        return {
            'profile': self.obj,
            'memberships': [
                membership.current_access(datasets=('without_parent', 'related'))
                for membership in self.obj.organization.active_admin_memberships
            ],
        }

    @route('new', methods=['GET', 'POST'])
    @render_with(json=True)
    @requires_login
    @requires_roles({'owner'})
    def new_member(self):
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
                        400,
                    )

                previous_membership = (
                    OrganizationMembership.query.filter(
                        OrganizationMembership.is_active
                    )
                    .filter_by(
                        organization=self.obj.organization,
                        user_id=membership_form.user.data.id,
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
                        400,
                    )
                else:
                    new_membership = OrganizationMembership(
                        organization=self.obj.organization, granted_by=current_auth.user
                    )
                    membership_form.populate_obj(new_membership)
                    db.session.add(new_membership)
                    db.session.commit()
                    dispatch_notification(
                        OrganizationAdminMembershipNotification(
                            document=new_membership.organization,
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
                            for membership in self.obj.organization.active_admin_memberships
                        ],
                    }
            else:
                return (
                    {
                        'status': 'error',
                        'error_description': _("The new admin could not be added"),
                        'errors': membership_form.errors,
                        'form_nonce': membership_form.form_nonce.data,
                    },
                    400,
                )

        membership_form_html = render_form(
            form=membership_form,
            title='',
            submit='Add member',
            ajax=False,
            with_chrome=False,
        )
        return {'form': membership_form_html}


OrganizationMembersView.init_app(app)


@OrganizationMembership.views('main')
@route('/<profile>/members/<membership>')
class OrganizationMembershipView(
    ProfileCheckMixin, UrlChangeCheck, UrlForView, ModelView
):
    model = OrganizationMembership
    route_model_map = {'profile': 'organization.name', 'membership': 'uuid_b58'}
    obj: OrganizationMembership

    def loader(self, profile, membership) -> OrganizationMembership:
        return OrganizationMembership.query.filter(
            OrganizationMembership.uuid_b58 == membership,
        ).first_or_404()

    def after_loader(self) -> Optional[ReturnView]:
        self.profile = self.obj.organization.profile
        return super().after_loader()

    @route('edit', methods=['GET', 'POST'])
    @render_with(json=True)
    @requires_login
    @requires_roles({'profile_owner'})
    def edit(self):
        previous_membership = self.obj
        membership_form = OrganizationMembershipForm(obj=previous_membership)

        if request.method == 'POST':
            if membership_form.validate_on_submit():
                if previous_membership.user == current_auth.user:
                    return {
                        'status': 'error',
                        'error_description': _("You can’t edit your own role"),
                        'form_nonce': membership_form.form_nonce.data,
                    }

                try:
                    new_membership = previous_membership.replace(
                        actor=current_auth.user, is_owner=membership_form.is_owner.data
                    )
                except MembershipRevokedError:
                    return (
                        {
                            'status': 'error',
                            'error_description': _(
                                "This member’s record was edited elsewhere."
                                " Reload the page"
                            ),
                            'form_nonce': membership_form.form_nonce.data,
                        },
                        400,
                    )
                if new_membership != previous_membership:
                    db.session.commit()
                    dispatch_notification(
                        OrganizationAdminMembershipNotification(
                            document=new_membership.organization,
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
                        for membership in self.obj.organization.active_admin_memberships
                    ],
                }
            else:
                return (
                    {
                        'status': 'error',
                        'error_description': _("Please pick one or more roles"),
                        'errors': membership_form.errors,
                        'form_nonce': membership_form.form_nonce.data,
                    },
                    400,
                )

        membership_form_html = render_form(
            form=membership_form,
            title='',
            submit='Edit membership',
            ajax=False,
            with_chrome=False,
        )
        return {'form': membership_form_html}

    @route('delete', methods=['GET', 'POST'])
    @render_with(json=True)
    @requires_sudo
    @requires_roles({'profile_owner'})
    def delete(self):
        form = Form()
        if form.is_submitted():
            if form.validate():
                previous_membership = self.obj
                if previous_membership.user == current_auth.user:
                    return {
                        'status': 'error',
                        'error_description': _("You can’t revoke your own membership"),
                        'form_nonce': form.form_nonce.data,
                    }
                if previous_membership.is_active:
                    previous_membership.revoke(actor=current_auth.user)
                    db.session.commit()
                    dispatch_notification(
                        OrganizationAdminMembershipRevokedNotification(
                            document=previous_membership.organization,
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
                        for membership in self.obj.organization.active_admin_memberships
                    ],
                }
            else:
                return (
                    {
                        'status': 'error',
                        'errors': form.errors,
                        'form_nonce': form.form_nonce.data,
                    },
                    400,
                )

        form_html = render_form(
            form=form,
            title=_("Confirm removal"),
            message=_("Remove {member} as an admin from {profile}?").format(
                member=self.obj.user.fullname, profile=self.obj.organization.title
            ),
            submit=_("Remove"),
            ajax=False,
            with_chrome=False,
        )
        return {'form': form_html}


OrganizationMembershipView.init_app(app)


#: Project Membership views


@Project.views('crew')
@route('/<profile>/<project>/crew')
class ProjectMembershipView(ProjectViewMixin, UrlChangeCheck, UrlForView, ModelView):
    @route('', methods=['GET', 'POST'])
    @render_with('project_membership.html.jinja2')
    def crew(self):
        return {
            'project': self.obj,
            'memberships': [
                membership.current_access(datasets=('without_parent', 'related'))
                for membership in self.obj.active_crew_memberships
            ],
        }

    @route('new', methods=['GET', 'POST'])
    @render_with(json=True)
    @requires_login
    @requires_roles({'profile_admin'})
    def new_member(self):
        membership_form = ProjectCrewMembershipForm()

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
                        400,
                    )
                previous_membership = (
                    ProjectCrewMembership.query.filter(ProjectCrewMembership.is_active)
                    .filter_by(project=self.obj, user_id=membership_form.user.data.id)
                    .one_or_none()
                )
                if previous_membership is not None:
                    return (
                        {
                            'status': 'error',
                            'error_description': _("This person is already a member"),
                            'errors': membership_form.errors,
                            'form_nonce': membership_form.form_nonce.data,
                        },
                        400,
                    )
                else:
                    new_membership = ProjectCrewMembership(
                        project=self.obj, granted_by=current_auth.user
                    )
                    membership_form.populate_obj(new_membership)
                    db.session.add(new_membership)
                    # TODO: Once invite is introduced, send invite email here
                    db.session.commit()
                    signals.project_role_change.send(
                        self.obj, actor=current_auth.user, user=new_membership.user
                    )
                    signals.project_crew_membership_added.send(
                        self.obj,
                        project=self.obj,
                        membership=new_membership,
                        actor=current_auth.user,
                        user=new_membership.user,
                    )
                    db.session.commit()
                    return {
                        'status': 'ok',
                        'message': _("The user has been added as a member"),
                        'memberships': [
                            membership.current_access(
                                datasets=('without_parent', 'related')
                            )
                            for membership in self.obj.active_crew_memberships
                        ],
                    }
            else:
                return (
                    {
                        'status': 'error',
                        'error_description': _("The new member could not be added"),
                        'errors': membership_form.errors,
                        'form_nonce': membership_form.form_nonce.data,
                    },
                    400,
                )

        membership_form_html = render_form(
            form=membership_form,
            title='',
            submit='Add member',
            ajax=False,
            with_chrome=False,
        )
        return {'form': membership_form_html}


ProjectMembershipView.init_app(app)


class ProjectCrewMembershipMixin(ProfileCheckMixin):
    model = ProjectCrewMembership
    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'membership': 'uuid_b58',
    }
    obj: ProjectCrewMembership

    def loader(self, profile, project, membership) -> ProjectCrewMembership:
        return (
            ProjectCrewMembership.query.join(Project, Profile)
            .filter(
                db.func.lower(Profile.name) == db.func.lower(profile),
                Project.name == project,
                ProjectCrewMembership.uuid_b58 == membership,
            )
            .first_or_404()
        )

    def after_loader(self) -> Optional[ReturnView]:
        self.profile = self.obj.project.profile
        return super().after_loader()


@ProjectCrewMembership.views('invite')
@route('/<profile>/<project>/crew/<membership>/invite')
class ProjectCrewMembershipInviteView(
    ProjectCrewMembershipMixin, UrlChangeCheck, UrlForView, ModelView
):
    def loader(self, profile, project, membership) -> ProjectCrewMembership:
        obj = super().loader(profile, project, membership)
        if not obj.is_invite or obj.user != current_auth.user:
            abort(404)
        return obj

    @route('', methods=['GET'])
    @render_with('membership_invite_actions.html.jinja2')
    @requires_login
    def invite(self):
        return {
            'membership': self.obj.current_access(datasets=('primary', 'related')),
            'form': Form(),
        }

    @route('action', methods=['POST'])
    @requires_login
    def invite_action(self):
        membership_invite_form = ProjectCrewMembershipInviteForm()
        if membership_invite_form.validate_on_submit():
            if membership_invite_form.action.data == 'accept':
                self.obj.accept(actor=current_auth.user)
            elif membership_invite_form.action.data == 'decline':
                self.obj.revoke(actor=current_auth.user)
            db.session.commit()
        return redirect(self.obj.project.url_for(), 303)


ProjectCrewMembershipInviteView.init_app(app)


@ProjectCrewMembership.views('main')
@route('/<profile>/<project>/crew/<membership>')
class ProjectCrewMembershipView(
    ProjectCrewMembershipMixin, UrlChangeCheck, UrlForView, ModelView
):
    @route('edit', methods=['GET', 'POST'])
    @render_with(json=True)
    @requires_login
    @requires_roles({'profile_admin'})
    def edit(self):
        previous_membership = self.obj
        form = ProjectCrewMembershipForm(obj=previous_membership)

        if form.is_submitted():
            if form.validate():
                try:
                    previous_membership.replace(
                        actor=current_auth.user,
                        is_editor=form.is_editor.data,
                        is_promoter=form.is_promoter.data,
                        is_usher=form.is_usher.data,
                    )
                except MembershipRevokedError:
                    return (
                        {
                            'status': 'error',
                            'error_description': _(
                                "The member’s record was edited elsewhere."
                                " Reload the page"
                            ),
                            'form_nonce': form.form_nonce.data,
                        },
                        400,
                    )
                db.session.commit()
                signals.project_role_change.send(
                    self.obj.project, actor=current_auth.user, user=self.obj.user
                )
                db.session.commit()
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
            else:
                return (
                    {
                        'status': 'error',
                        'error_description': _("Please pick one or more roles"),
                        'errors': form.errors,
                        'form_nonce': form.form_nonce.data,
                    },
                    400,
                )

        membership_form_html = render_form(
            form=form,
            title='',
            submit='Edit membership',
            ajax=False,
            with_chrome=False,
        )
        return {'form': membership_form_html}

    @route('delete', methods=['GET', 'POST'])
    @render_with(json=True)
    @requires_sudo
    @requires_roles({'profile_admin'})
    def delete(self):
        form = Form()
        if request.method == 'POST':
            if form.validate_on_submit():
                previous_membership = self.obj
                if previous_membership.is_active:
                    previous_membership.revoke(actor=current_auth.user)
                    signals.project_crew_membership_revoked.send(
                        self.obj.project,
                        project=self.obj.project,
                        membership=previous_membership,
                        actor=current_auth.user,
                        user=previous_membership.user,
                    )
                    db.session.commit()
                    signals.project_role_change.send(
                        self.obj.project, actor=current_auth.user, user=self.obj.user
                    )
                    db.session.commit()
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
            else:
                return ({'status': 'error', 'errors': form.errors}, 400)

        form_html = render_form(
            form=form,
            title=_("Confirm removal"),
            message=_("Remove {member} as a crew member from this project?").format(
                member=self.obj.user.fullname
            ),
            submit=_("Remove"),
            ajax=False,
            with_chrome=False,
        )
        return {'form': form_html}


ProjectCrewMembershipView.init_app(app)
