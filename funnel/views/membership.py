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

from .. import app, funnelapp, lastuser
from ..forms import (
    ProfileAdminMembershipForm,
    ProjectCrewMembershipForm,
    ProjectCrewMembershipInviteForm,
    SavedProjectForm,
)
from ..jobs import send_mail_async
from ..models import Profile, ProfileAdminMembership, Project, ProjectCrewMembership, db
from .decorators import legacy_redirect
from .mixins import ProfileViewMixin, ProjectViewMixin


@route('/<profile>/membership')
class ProfileMembershipView(ProfileViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('', methods=['GET', 'POST'])
    @render_with('profile_membership.html.jinja2')
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
    @lastuser.requires_login
    @requires_roles({'owner'})
    def new_member(self):
        membership_form = ProfileAdminMembershipForm()

        if request.method == 'POST':
            if membership_form.validate_on_submit():
                previous_membership = (
                    ProfileAdminMembership.query.filter(
                        ProfileAdminMembership.is_active
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
                    new_membership = ProfileAdminMembership(
                        parent_id=self.obj.id, granted_by=current_auth.user
                    )
                    membership_form.populate_obj(new_membership)
                    db.session.add(new_membership)
                    db.session.commit()

                    send_mail_async.queue(
                        sender=None,
                        to=new_membership.user.email,
                        body=render_template(
                            'profile_membership_add_email.md',
                            granted_by=new_membership.granted_by,
                            profile=self.obj,
                            profile_membership_link=self.obj.url_for(
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


@route('/membership', subdomain='<profile>')
class FunnelProfileMembershipView(ProfileMembershipView):
    pass


ProfileMembershipView.init_app(app)
FunnelProfileMembershipView.init_app(funnelapp)


@route('/<profile>/membership/<suuid>')
class ProfileAdminMembershipView(UrlChangeCheck, UrlForView, ModelView):
    model = ProfileAdminMembership
    __decorators__ = [legacy_redirect]

    route_model_map = {'profile': 'profile.name', 'suuid': 'suuid'}

    def loader(self, profile, suuid):
        membership = (
            self.model.query.join(Profile)
            .filter(Profile.name == profile, ProfileAdminMembership.suuid == suuid)
            .first_or_404()
        )
        return membership

    def after_loader(self):
        g.profile = self.obj.profile
        super(ProfileAdminMembershipView, self).after_loader()

    @route('edit', methods=['GET', 'POST'])
    @render_with(json=True)
    @lastuser.requires_login
    @requires_roles({'profile_owner'})
    def edit(self):
        previous_membership = self.obj
        membership_form = ProfileAdminMembershipForm(obj=previous_membership)

        if request.method == 'POST':
            if membership_form.validate_on_submit():
                primary_owner_membership = self.obj.profile.active_admin_memberships.order_by(
                    ProfileAdminMembership.granted_at.asc()
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
    @lastuser.requires_login
    @requires_roles({'profile_owner'})
    def delete(self):
        form = Form()
        if request.method == 'POST':
            if form.validate_on_submit():
                primary_owner_membership = self.obj.profile.active_admin_memberships.order_by(
                    ProfileAdminMembership.granted_at.asc()
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
                            'profile_membership_revoke_notification_email.md',
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


@route('/membership/<suuid>', subdomain='<profile>')
class FunnelProfileAdminMembershipView(ProfileAdminMembershipView):
    pass


ProfileAdminMembershipView.init_app(app)
FunnelProfileAdminMembershipView.init_app(funnelapp)


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
    @lastuser.requires_login
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
                            'project_membership_add_email.md',
                            # 'project_membership_add_invite_email.md',
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
        'suuid': 'suuid',
    }

    def loader(self, profile, project, suuid):
        membership = (
            self.model.query.join(Project, Profile)
            .filter(
                Profile.name == profile,
                Project.name == project,
                ProjectCrewMembership.suuid == suuid,
            )
            .first_or_404()
        )
        return membership

    def after_loader(self):
        g.profile = self.obj.project.profile
        super(ProjectCrewMembershipMixin, self).after_loader()


@route('/<profile>/<project>/membership/<suuid>/invite')
class ProjectCrewMembershipInviteView(
    ProjectCrewMembershipMixin, UrlChangeCheck, UrlForView, ModelView
):
    __decorators__ = [legacy_redirect]

    def loader(self, profile, project, suuid):
        membership = super(ProjectCrewMembershipInviteView, self).loader(
            profile, project, suuid
        )
        if not membership.is_invite or membership.user != current_auth.user:
            raise abort(404)

        return membership

    @route('', methods=['GET'])
    @render_with('membership_invite_actions.html.jinja2')
    @lastuser.requires_login
    def invite(self):
        return {'membership': self.obj.current_access(), 'form': Form()}

    @route('action', methods=['POST'])
    @lastuser.requires_login
    def invite_action(self):
        membership_invite_form = ProjectCrewMembershipInviteForm()
        if membership_invite_form.validate_on_submit():
            if membership_invite_form.action.data == 'accept':
                self.obj.accept(actor=current_auth.user)
            elif membership_invite_form.action.data == 'decline':
                self.obj.revoke(actor=current_auth.user)
            db.session.commit()
        return redirect(self.obj.project.url_for(), 303)


@route('/<project>/membership/<suuid>/invite', subdomain='<profile>')
class FunnelProjectCrewMembershipInviteView(ProjectCrewMembershipInviteView):
    pass


ProjectCrewMembershipInviteView.init_app(app)
FunnelProjectCrewMembershipInviteView.init_app(funnelapp)


@route('/<profile>/<project>/membership/<suuid>')
class ProjectCrewMembershipView(
    ProjectCrewMembershipMixin, UrlChangeCheck, UrlForView, ModelView
):
    __decorators__ = [legacy_redirect]

    @route('edit', methods=['GET', 'POST'])
    @render_with(json=True)
    @lastuser.requires_login
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
    @lastuser.requires_login
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
                            'project_membership_revoke_notification_email.md',
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


@route('/<project>/membership/<suuid>', subdomain='<profile>')
class FunnelProjectCrewMembershipView(ProjectCrewMembershipView):
    pass


ProjectCrewMembershipView.init_app(app)
FunnelProjectCrewMembershipView.init_app(funnelapp)
