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
    ProjectCrewMembershipForm,
    ProjectCrewMembershipInviteForm,
    SavedProjectForm,
)
from ..jobs import send_mail_async
from ..models import MEMBERSHIP_RECORD_TYPE, Profile, Project, ProjectCrewMembership, db
from .decorators import legacy_redirect
from .mixins import ProjectViewMixin


@route('/<profile>/<project>/membership')
class ProjectMembershipView(ProjectViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('', methods=['GET', 'POST'])
    @render_with('membership.html.jinja2')
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
                    ProjectCrewMembership.query.filter(ProjectCrewMembership.active)
                    .filter_by(project=self.obj, user=membership_form.user.data)
                    .one_or_none()
                )
                if previous_membership is not None:
                    return (
                        {
                            'status': 'error',
                            'message': _("Member already exists in the project"),
                        },
                        400,
                    )
                else:
                    new_membership = ProjectCrewMembership(
                        project=self.obj, granted_by=current_auth.user
                    )
                    membership_form.populate_obj(new_membership)
                    new_membership.record_type = MEMBERSHIP_RECORD_TYPE.DIRECT_ADD
                    db.session.add(new_membership)
                    db.session.commit()

                    # TODO: Once invite is introduced, send invite email here
                    send_mail_async.queue(
                        sender=None,
                        to=new_membership.user.email,
                        body=render_template(
                            'membership_add_email.md',
                            # 'membership_add_invite_email.md',
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
    @requires_roles({'editor'})
    def edit(self):
        previous_membership = self.obj
        membership_form = ProjectCrewMembershipForm(obj=previous_membership)

        if request.method == 'POST':
            if membership_form.validate_on_submit():
                previous_membership.replace(
                    actor=current_auth.user,
                    record_type=MEMBERSHIP_RECORD_TYPE.AMEND,
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
    @requires_roles({'editor'})
    def delete(self):
        form = Form()
        if request.method == 'POST':
            if form.validate_on_submit():
                previous_membership = self.obj
                if previous_membership.active:
                    previous_membership.revoke(actor=current_auth.user)
                    db.session.commit()

                    send_mail_async.queue(
                        sender=None,
                        to=previous_membership.user.email,
                        body=render_template(
                            'membership_revoke_notification_email.md',
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
            ).format(member=self.obj.user_details['fullname']),
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
