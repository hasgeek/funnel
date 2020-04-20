# -*- coding: utf-8 -*-

from flask import abort, g, redirect, render_template, request

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

from .. import app, funnelapp
from ..forms import (
    OrganizationMembershipForm,
    ProjectCrewMembershipForm,
    ProjectCrewMembershipInviteForm,
    SavedProjectForm,
)
from ..jobs import send_mail_async
from ..models import OrganizationMembership, Profile, Project, ProjectCrewMembership, db
from .decorators import legacy_redirect
from .helpers import requires_login
from .mixins import ProfileViewMixin, ProjectViewMixin


@route('/<profile>/membership')
class OrganizationMembersView(ProfileViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('', methods=['GET', 'POST'])
    @render_with('organization_membership.html.jinja2')
    @requires_roles({'admin'})
    def membership(self):
        return {
            'profile': self.obj,
            'memberships': [
                membership.current_access()
                for membership in self.obj.active_admin_memberships
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
                previous_membership = (
                    OrganizationMembership.query.filter(
                        OrganizationMembership.is_active
                    )
                    .filter_by(profile=self.obj, user_id=membership_form.user.data.id)
                    .one_or_none()
                )
                if previous_membership is not None:
                    return (
                        {
                            'status': 'error',
                            'message': _("Member already exists in the profile"),
                            'errors': membership_form.errors,
                        },
                        400,
                    )
                else:
                    new_membership = OrganizationMembership(
                        parent_id=self.obj.id, granted_by=current_auth.user
                    )
                    membership_form.populate_obj(new_membership)
                    db.session.add(new_membership)
                    db.session.commit()

                    send_mail_async.queue(
                        sender=None,
                        to=new_membership.user.email,
                        body=render_template(
                            'organization_membership_add_email.md.jinja2',
                            granted_by=new_membership.granted_by,
                            profile=self.obj,
                            organization_membership_link=self.obj.url_for(
                                'membership', _external=True
                            ),
                        ),
                        subject=_("You have been added to {} as a admin").format(
                            self.obj.title
                        ),
                    )
                    return {
                        'status': 'ok',
                        'message': _("The user has been added as an admin"),
                        'memberships': [
                            membership.current_access()
                            for membership in self.obj.active_admin_memberships
                        ],
                    }
            else:
                return (
                    {
                        'status': 'error',
                        'message': _("The new member could not be added"),
                        'errors': membership_form.errors,
                    },
                    400,
                )

        membership_form_html = render_form(
            form=membership_form,
            title='',
            submit=u'Add member',
            ajax=False,
            with_chrome=False,
        )
        return {'form': membership_form_html}


OrganizationMembersView.init_app(app)


@route('/<profile>/membership/<membership>')
class OrganizationMembershipView(UrlChangeCheck, UrlForView, ModelView):
    model = OrganizationMembership
    __decorators__ = [legacy_redirect]

    route_model_map = {'profile': 'profile.name', 'membership': 'uuid_b58'}

    def loader(self, profile, membership):
        obj = (
            self.model.query.join(Profile)
            .filter(
                Profile.name == profile, OrganizationMembership.uuid_b58 == membership
            )
            .first_or_404()
        )
        return obj

    def after_loader(self):
        g.profile = self.obj.profile
        super(OrganizationMembershipView, self).after_loader()

    @route('edit', methods=['GET', 'POST'])
    @render_with(json=True)
    @requires_login
    @requires_roles({'profile_owner'})
    def edit(self):
        previous_membership = self.obj
        membership_form = OrganizationMembershipForm(obj=previous_membership)

        if request.method == 'POST':
            if membership_form.validate_on_submit():
                primary_owner_membership = self.obj.profile.active_admin_memberships.order_by(
                    OrganizationMembership.granted_at.asc()
                ).first()

                if (
                    membership_form.user.data == primary_owner_membership.user
                    and current_auth.user != primary_owner_membership.user
                ):
                    # the primary(first) owner membership can't be modified by others
                    return {
                        'status': 'error',
                        'message': _("Cannot modify the primary owner of the profile"),
                    }

                previous_membership.replace(
                    actor=current_auth.user, is_owner=membership_form.is_owner.data
                )
                db.session.commit()
                return {
                    'status': 'ok',
                    'memberships': [
                        membership.current_access()
                        for membership in self.obj.profile.active_admin_memberships
                    ],
                }
            else:
                return (
                    {
                        'status': 'error',
                        'message': _("At lease one role must be chosen"),
                        'errors': membership_form.errors,
                    },
                    400,
                )

        membership_form_html = render_form(
            form=membership_form,
            title='',
            submit=u'Edit membership',
            ajax=False,
            with_chrome=False,
        )
        return {'form': membership_form_html}

    @route('delete', methods=['GET', 'POST'])
    @render_with(json=True)
    @requires_login
    @requires_roles({'profile_owner'})
    def delete(self):
        form = Form()
        if request.method == 'POST':
            if form.validate_on_submit():
                primary_owner_membership = self.obj.profile.active_admin_memberships.order_by(
                    OrganizationMembership.granted_at.asc()
                ).first()

                if (
                    self.obj.user == primary_owner_membership.user
                    and current_auth.user != primary_owner_membership.user
                ):
                    # the primary(first) owner membership can't be deleted by others
                    return {
                        'status': 'error',
                        'message': _("Cannot delete the primary owner of the profile"),
                    }

                previous_membership = self.obj
                if previous_membership.is_active:
                    previous_membership.revoke(actor=current_auth.user)
                    db.session.commit()

                    send_mail_async.queue(
                        sender=None,
                        to=previous_membership.user.email,
                        body=render_template(
                            'organization_membership_revoke_notification_email.md.jinja2',
                            revoked_by=current_auth.user,
                            profile=self.obj.profile,
                        ),
                        subject=_("You have been removed from {} as a member").format(
                            self.obj.profile.title
                        ),
                    )
                return {
                    'status': 'ok',
                    'memberships': [
                        membership.current_access()
                        for membership in self.obj.profile.active_admin_memberships
                    ],
                }
            else:
                return ({'status': 'error', 'errors': form.errors}, 400)

        form_html = render_form(
            form=form,
            title=_("Delete member"),
            message=_(
                "Are you sure you want to remove {member} from {profile} as an admin?"
            ).format(member=self.obj.user.fullname, profile=self.obj.profile.title),
            submit=_("Delete"),
            ajax=False,
            with_chrome=False,
        )
        return {'form': form_html}


OrganizationMembershipView.init_app(app)


#: Project Membership views


@route('/<profile>/<project>/membership')
class ProjectMembershipView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('', methods=['GET', 'POST'])
    @render_with('project_membership.html.jinja2')
    def membership(self):
        project_save_form = SavedProjectForm()
        return {
            'project': self.obj,
            'memberships': [
                membership.current_access()
                for membership in self.obj.active_crew_memberships
            ],
            'project_save_form': project_save_form,
        }

    @route('new', methods=['GET', 'POST'])
    @render_with(json=True)
    @requires_login
    @requires_roles({'profile_admin'})
    def new_member(self):
        membership_form = ProjectCrewMembershipForm()

        if request.method == 'POST':
            if membership_form.validate_on_submit():
                previous_membership = (
                    ProjectCrewMembership.query.filter(ProjectCrewMembership.is_active)
                    .filter_by(project=self.obj, user_id=membership_form.user.data.id)
                    .one_or_none()
                )
                if previous_membership is not None:
                    return (
                        {
                            'status': 'error',
                            'message': _("Member already exists in the project"),
                            'errors': membership_form.errors,
                        },
                        400,
                    )
                else:
                    new_membership = ProjectCrewMembership(
                        parent_id=self.obj.id, granted_by=current_auth.user
                    )
                    membership_form.populate_obj(new_membership)
                    db.session.add(new_membership)
                    db.session.commit()

                    # TODO: Once invite is introduced, send invite email here
                    send_mail_async.queue(
                        sender=None,
                        to=new_membership.user.email,
                        body=render_template(
                            'project_membership_add_email.md.jinja2',
                            # 'project_membership_add_invite_email.md.jinja2',
                            granted_by=new_membership.granted_by,
                            project=self.obj,
                            project_membership_link=self.obj.url_for(
                                'membership', _external=True
                            )
                            # link=new_membership.url_for('invite', _external=True),
                        ),
                        subject=_("You have been added to {} as a member").format(
                            self.obj.title
                        ),
                    )
                    return {
                        'status': 'ok',
                        'message': _("The user has been added as a member"),
                        'memberships': [
                            membership.current_access()
                            for membership in self.obj.active_crew_memberships
                        ],
                    }
            else:
                return (
                    {
                        'status': 'error',
                        'message': _("The new member could not be added"),
                        'errors': membership_form.errors,
                    },
                    400,
                )

        membership_form_html = render_form(
            form=membership_form,
            title='',
            submit=u'Add member',
            ajax=False,
            with_chrome=False,
        )
        return {'form': membership_form_html}


@route('/<project>/membership', subdomain='<profile>')
class FunnelProjectMembershipView(ProjectMembershipView):
    pass


ProjectMembershipView.init_app(app)
FunnelProjectMembershipView.init_app(funnelapp)


class ProjectCrewMembershipMixin(object):
    model = ProjectCrewMembership

    route_model_map = {
        'profile': 'project.profile.name',
        'project': 'project.name',
        'membership': 'uuid_b58',
    }

    def loader(self, profile, project, membership):
        obj = (
            self.model.query.join(Project, Profile)
            .filter(
                Profile.name == profile,
                Project.name == project,
                ProjectCrewMembership.uuid_b58 == membership,
            )
            .first_or_404()
        )
        return obj

    def after_loader(self):
        g.profile = self.obj.project.profile
        super(ProjectCrewMembershipMixin, self).after_loader()


@route('/<profile>/<project>/membership/<membership>/invite')
class ProjectCrewMembershipInviteView(
    ProjectCrewMembershipMixin, UrlChangeCheck, UrlForView, ModelView
):
    __decorators__ = [legacy_redirect]

    def loader(self, profile, project, membership):
        obj = super().loader(profile, project, membership)
        if not obj.is_invite or obj.user != current_auth.user:
            raise abort(404)

        return obj

    @route('', methods=['GET'])
    @render_with('membership_invite_actions.html.jinja2')
    @requires_login
    def invite(self):
        return {'membership': self.obj.current_access(), 'form': Form()}

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


@route('/<project>/membership/<membership>/invite', subdomain='<profile>')
class FunnelProjectCrewMembershipInviteView(ProjectCrewMembershipInviteView):
    pass


ProjectCrewMembershipInviteView.init_app(app)
FunnelProjectCrewMembershipInviteView.init_app(funnelapp)


@route('/<profile>/<project>/membership/<membership>')
class ProjectCrewMembershipView(
    ProjectCrewMembershipMixin, UrlChangeCheck, UrlForView, ModelView
):
    __decorators__ = [legacy_redirect]

    @route('edit', methods=['GET', 'POST'])
    @render_with(json=True)
    @requires_login
    @requires_roles({'profile_admin'})
    def edit(self):
        previous_membership = self.obj
        membership_form = ProjectCrewMembershipForm(obj=previous_membership)

        if request.method == 'POST':
            if membership_form.validate_on_submit():
                previous_membership.replace(
                    actor=current_auth.user,
                    is_editor=membership_form.is_editor.data,
                    is_concierge=membership_form.is_concierge.data,
                    is_usher=membership_form.is_usher.data,
                )
                db.session.commit()
                return {
                    'status': 'ok',
                    'memberships': [
                        membership.current_access()
                        for membership in self.obj.project.active_crew_memberships
                    ],
                }
            else:
                return (
                    {
                        'status': 'error',
                        'message': _("At lease one role must be chosen"),
                        'errors': membership_form.errors,
                    },
                    400,
                )

        membership_form_html = render_form(
            form=membership_form,
            title='',
            submit=u'Edit membership',
            ajax=False,
            with_chrome=False,
        )
        return {'form': membership_form_html}

    @route('delete', methods=['GET', 'POST'])
    @render_with(json=True)
    @requires_login
    @requires_roles({'profile_admin'})
    def delete(self):
        form = Form()
        if request.method == 'POST':
            if form.validate_on_submit():
                previous_membership = self.obj
                if previous_membership.is_active:
                    previous_membership.revoke(actor=current_auth.user)
                    db.session.commit()

                    send_mail_async.queue(
                        sender=None,
                        to=previous_membership.user.email,
                        body=render_template(
                            'project_membership_revoke_notification_email.md.jinja2',
                            revoked_by=current_auth.user,
                            project=self.obj.project,
                        ),
                        subject=_("You have been removed from {} as a member").format(
                            self.obj.project.title
                        ),
                    )
                return {
                    'status': 'ok',
                    'memberships': [
                        membership.current_access()
                        for membership in self.obj.project.active_crew_memberships
                    ],
                }
            else:
                return ({'status': 'error', 'errors': form.errors}, 400)

        form_html = render_form(
            form=form,
            title=_("Delete member"),
            message=_(
                "Are you sure you want to remove {member} from the project?"
            ).format(member=self.obj.user.fullname),
            submit=_("Delete"),
            ajax=False,
            with_chrome=False,
        )
        return {'form': form_html}


@route('/<project>/membership/<membership>', subdomain='<profile>')
class FunnelProjectCrewMembershipView(ProjectCrewMembershipView):
    pass


ProjectCrewMembershipView.init_app(app)
FunnelProjectCrewMembershipView.init_app(funnelapp)
