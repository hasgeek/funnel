# -*- coding: utf-8 -*-

from flask import Markup, flash, g, redirect, request, url_for

from baseframe import _
from baseframe.forms import render_form, render_message, render_redirect
from coaster.views import (
    ModelView,
    UrlForView,
    jsonp,
    render_with,
    requires_permission,
    route,
)

from .. import app, funnelapp, lastuser
from ..forms import EditProfileForm, NewProfileForm
from ..models import Profile, Project, Team, db
from .decorators import legacy_redirect
from .mixins import ProfileViewMixin
from .project import project_data


# @app.route('/new', methods=['GET', 'POST'])  # Disabled on 8 Dec, 2018
@lastuser.requires_scope('teams')
def profile_new():
    # Step 1: Get a list of organizations this user owns
    existing = Profile.query.filter(
        Profile.userid.in_(g.user.organizations_owned_ids())
    ).all()
    existing_ids = [e.userid for e in existing]
    # Step 2: Prune list to organizations without a profile
    new_profiles = []
    for org in g.user.organizations_owned():
        if org['userid'] not in existing_ids:
            new_profiles.append((org['userid'], org['title']))
    if not new_profiles:
        return render_message(
            title=_(u"No organizations found"),
            message=Markup(
                _(
                    u"You do not have any organizations that do not already have a Talkfunnel. "
                    u'Would you like to <a href="{link}">create a new organization</a>?'
                ).format(link=lastuser.endpoint_url('/organizations/new'))
            ),
        )
    eligible_profiles = []
    for orgid, title in new_profiles:
        if Team.query.filter_by(orgid=orgid).first() is not None:
            eligible_profiles.append((orgid, title))
    if not eligible_profiles:
        return render_message(
            title=_(u"No organizations available"),
            message=_(
                u"To create a Talkfunnel for an organization, you must be the owner of the organization."
            ),
        )

    # Step 3: Ask user to select organization
    form = NewProfileForm()
    form.profile.choices = eligible_profiles
    if request.method == 'GET':
        form.profile.data = new_profiles[0][0]
    if form.validate_on_submit():
        # Step 4: Make a profile
        org = [
            org
            for org in g.user.organizations_owned()
            if org['userid'] == form.profile.data
        ][0]
        profile = Profile(name=org['name'], title=org['title'], userid=org['userid'])
        db.session.add(profile)
        db.session.commit()
        flash(
            _(u"Created a profile for {profile}").format(profile=profile.title),
            "success",
        )
        return render_redirect(profile.url_for('edit'), code=303)
    return render_form(
        form=form,
        title=_(u"Create a Talkfunnel for your organization..."),
        message=_(
            u"Talkfunnel is a free service while in beta. Sign up now to help us test the service."
        ),
        submit="Next",
        formid="profile_new",
        cancel_url=url_for('index'),
        ajax=False,
    )


@route('/<profile>')
class ProfileView(ProfileViewMixin, UrlForView, ModelView):
    __decorators__ = [legacy_redirect]

    @route('')
    @render_with('index.html.jinja2', json=True)
    @requires_permission('view')
    def view(self):
        # `order_by(None)` clears any existing order defined in relationship.
        # We're using it because we want to define our own order here.
        projects = self.obj.listed_projects.order_by(None)
        past_projects = (
            projects.filter(Project.state.PUBLISHED, Project.schedule_state.PAST)
            .order_by(Project.schedule_start_at.desc())
            .all()
        )
        all_projects = (
            projects.filter(
                Project.state.PUBLISHED,
                db.or_(Project.schedule_state.LIVE, Project.schedule_state.UPCOMING),
            )
            .order_by(Project.schedule_start_at.asc())
            .all()
        )
        upcoming_projects = all_projects[:3]
        all_projects = all_projects[3:]
        featured_project = (
            projects.filter(
                Project.state.PUBLISHED,
                db.or_(Project.schedule_state.LIVE, Project.schedule_state.UPCOMING),
                Project.featured.is_(True),
            )
            .order_by(Project.schedule_start_at.asc())
            .limit(1)
            .first()
        )
        if featured_project in upcoming_projects:
            upcoming_projects.remove(featured_project)
        open_cfp_projects = (
            projects.filter(Project.state.PUBLISHED, Project.cfp_state.OPEN)
            .order_by(Project.schedule_start_at.asc())
            .all()
        )
        draft_projects = [
            proj for proj in self.obj.draft_projects if proj.current_roles.admin
        ]
        return {
            'profile': self.obj.current_access(),
            'past_projects': [p.current_access() for p in past_projects],
            'all_projects': [p.current_access() for p in all_projects],
            'upcoming_projects': [p.current_access() for p in upcoming_projects],
            'open_cfp_projects': [p.current_access() for p in open_cfp_projects],
            'draft_projects': [p.current_access() for p in draft_projects],
            'featured_project': (
                featured_project.current_access() if featured_project else None
            ),
        }

    @route('json')
    @render_with(json=True)
    @requires_permission('view')
    def json(self):
        projects = Project.fetch_sorted().filter_by(profile=self.obj).all()
        return jsonp(
            projects=map(project_data, projects), spaces=map(project_data, projects)
        )  # FIXME: Remove when the native app switches over

    @route('edit', methods=['GET', 'POST'])
    @requires_permission('edit-profile')
    def edit(self):
        form = EditProfileForm(obj=self.obj, model=Profile)
        if form.validate_on_submit():
            form.populate_obj(self.obj)
            db.session.commit()
            flash(_("Your changes have been saved"), 'info')
            return redirect(self.obj.url_for(), code=303)
        return render_form(
            form=form,
            title=_("Edit project details"),
            submit=_("Save changes"),
            cancel_url=self.obj.url_for(),
            ajax=False,
        )


@route('/', subdomain='<profile>')
class FunnelProfileView(ProfileView):
    @route('')
    @render_with('funnelindex.html.jinja2')
    @requires_permission('view')
    def view(self):
        return {'profile': self.obj, 'projects': self.obj.listed_projects}


ProfileView.init_app(app)
FunnelProfileView.init_app(funnelapp)
