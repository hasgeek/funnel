# -*- coding: utf-8 -*-

from flask import g, Markup, request, flash, url_for
from baseframe.forms import render_message, render_redirect, render_form
from ..models import db, Profile, Team
from ..forms import NewProfileForm
from .. import app, lastuser


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
            title=u"No organizations found",
            message=Markup(u"You do not have any organizations that do not already have a talk funnel. "
                u'Would you like to <a href="%s">create a new organization</a>?' %
                    lastuser.endpoint_url('/organizations/new')))
    eligible_profiles = []
    for orgid, title in new_profiles:
        if Team.query.filter_by(orgid=orgid).first() is not None:
            eligible_profiles.append((orgid, title))
    if not eligible_profiles:
        return render_message(
            title=u"No organizations available",
            message=u"To create a talk funnel for an organization, you must be the owner of the organization.")

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
        flash(u"Created a profile for %s" % profile.title, "success")
        return render_redirect(url_for('profile_view', profile=profile.name), code=303)
    return render_form(form=form, title="Create a talk funnel for your organization...", submit="Next",
        formid="profile_new", cancel_url=url_for('index'), ajax=False)
