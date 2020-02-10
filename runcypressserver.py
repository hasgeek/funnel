# -*- coding: utf-8 -*-

import sys

from flask import Markup, flash, g, request, url_for

from baseframe import _
from baseframe.forms import render_form, render_message, render_redirect
from funnel import app, lastuser
from funnel.forms import NewProfileForm
from funnel.models import Profile, Team, db


@app.route('/new', methods=['GET', 'POST'])  # Disabled on 8 Dec, 2018
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
            title=_("No organizations found"),
            message=Markup(
                _(
                    "You do not have any organizations that do not already have a Talkfunnel. "
                    'Would you like to <a href="{link}">create a new organization</a>?'
                ).format(link=lastuser.endpoint_url('/organizations/new'))
            ),
        )
    eligible_profiles = []
    for orgid, title in new_profiles:
        if Team.query.filter_by(orgid=orgid).first() is not None:
            eligible_profiles.append((orgid, title))
    if not eligible_profiles:
        return render_message(
            title=_("No organizations available"),
            message=_(
                "To create a Talkfunnel for an organization, you must be the owner of the organization."
            ),
        )

    # Step 3: Ask user to select organization
    form = NewProfileForm()
    form.profile.choices = eligible_profiles
    if request.method == 'GET':
        form.profile.data = new_profiles[0][0]
    if form.validate_on_submit():
        # Step 4: Make a profile
        user_org = [
            org
            for org in g.user.organizations_owned()
            if org['userid'] == form.profile.data
        ][0]
        profile = Profile(
            name=user_org['name'], title=user_org['title'], userid=user_org['userid']
        )
        db.session.add(profile)
        db.session.commit()
        flash(
            _("Created a profile for {profile}").format(profile=profile.title),
            "success",
        )
        return render_redirect(profile.url_for('edit'), code=303)
    return render_form(
        form=form,
        title=_("Create a Talkfunnel for your organization..."),
        submit="Next",
        cancel_url=url_for('index'),
    )


try:
    port = int(sys.argv[1])
except (IndexError, ValueError):
    port = 3002
app.run('0.0.0.0', port=port, debug=True)
