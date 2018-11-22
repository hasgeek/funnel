# -*- coding: utf-8 -*-

from flask import g
from baseframe import _, __
import baseframe.forms as forms
from baseframe.forms.sqlalchemy import QuerySelectField
from ..models import Team


class NewProfileForm(forms.Form):
    """
    Create a new profile.
    """
    profile = forms.RadioField(__("Organization"), validators=[forms.validators.DataRequired("Select an organization")],
        description=__("Select the organization you’d like to create a Talkfunnel for"))


def profile_teams():
    return Team.query.filter_by(orgid=g.profile.userid).order_by(Team.title)


class EditProfileForm(forms.Form):
    """
    Edit a profile.
    """
    description = forms.MarkdownField(__("Welcome message"),
        validators=[forms.validators.DataRequired(_(u"Please write a message for the landing page"))],
        description=__("This welcome message will be shown on the landing page."))
    logo_url = forms.URLField(__("Logo URL"), description=__("Profile logo"),
        validators=[forms.validators.Optional(), forms.validators.Length(max=2000)])
    admin_team = QuerySelectField(u"Admin Team",
        validators=[forms.validators.DataRequired(_(u"Please select a team"))],
        query_factory=profile_teams, get_label='title', allow_blank=False,
        description=__("The team of users with administrative rights to this Talkfunnel (owners always have admin access)"))
