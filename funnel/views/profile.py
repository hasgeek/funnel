# -*- coding: utf-8 -*-

from flask import g, Markup, request, flash, url_for, redirect
from coaster.views import route, requires_permission, render_with, jsonp
from baseframe import _
from baseframe.forms import render_message, render_redirect, render_form
from ..models import db, Profile, Team, Project
from ..forms import NewProfileForm, EditProfileForm
from .. import app, funnelapp, lastuser
from .mixins import ProfileViewBaseMixin
from .project import project_data


@app.route('/new', methods=['GET', 'POST'])
@lastuser.requires_scope('teams')
def profile_new():
    # Step 1: Get a list of organizations this user owns
    existing = Profile.query.filter(Profile.userid.in_(g.user.organizations_owned_ids())).all()
    existing_ids = [e.userid for e in existing]
    # Step 2: Prune list to organizations without a profile
    new_profiles = []
    for org in g.user.organizations_owned():
        if org['userid'] not in existing_ids:
            new_profiles.append((org['userid'], org['title']))
    if not new_profiles:
        return render_message(
            title=_(u"No organizations found"),
            message=Markup(_(u"You do not have any organizations that do not already have a Talkfunnel. "
                u'Would you like to <a href="{link}">create a new organization</a>?').format(
                    link=lastuser.endpoint_url('/organizations/new'))))
    eligible_profiles = []
    for orgid, title in new_profiles:
        if Team.query.filter_by(orgid=orgid).first() is not None:
            eligible_profiles.append((orgid, title))
    if not eligible_profiles:
        return render_message(
            title=_(u"No organizations available"),
            message=_(u"To create a Talkfunnel for an organization, you must be the owner of the organization."))

    # Step 3: Ask user to select organization
    form = NewProfileForm()
    form.profile.choices = eligible_profiles
    if request.method == 'GET':
        form.profile.data = new_profiles[0][0]
    if form.validate_on_submit():
        # Step 4: Make a profile
        org = [org for org in g.user.organizations_owned() if org['userid'] == form.profile.data][0]
        profile = Profile(name=org['name'], title=org['title'], userid=org['userid'])
        db.session.add(profile)
        db.session.commit()
        flash(_(u"Created a profile for {profile}").format(profile=profile.title), "success")
        return render_redirect(profile.url_for('edit'), code=303)
    return render_form(
        form=form,
        title=_(u"Create a Talkfunnel for your organization..."),
        message=_(u"Talkfunnel is a free service while in beta. Sign up now to help us test the service."),
        submit="Next",
        formid="profile_new",
        cancel_url=url_for('index'),
        ajax=False)


@route('/<profile>')
class ProfileView(ProfileViewBaseMixin):
    @route('')
    @render_with('funnelindex.html.jinja2')
    @requires_permission('view')
    def view(self):
        return dict(profile=self.obj, projects=self.obj.parent_projects)

    @route('json')
    @render_with(json=True)
    @requires_permission('view')
    def json(self):
        projects = Project.fetch_sorted().filter_by(profile=self.obj).all()
        return jsonp(projects=map(project_data, projects),
            spaces=map(project_data, projects))  # FIXME: Remove when the native app switches over

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
            ajax=False)


@route('/', subdomain='<profile>')
class FunnelProfileView(ProfileView):
    pass


ProfileView.init_app(app)
FunnelProfileView.init_app(funnelapp)
