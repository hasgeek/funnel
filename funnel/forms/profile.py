# -*- coding: utf-8 -*-

from flask import g
from baseframe import _
import baseframe.forms as forms
from baseframe.forms.sqlalchemy import QuerySelectField
from ..models import Team


class NewProfileForm(forms.Form):
    """
    Create a new profile.
    """
    profile = forms.RadioField(u"Organization", validators=[forms.validators.DataRequired("Select an organization")],
        description=u"Select the organization you’d like to create a Talkfunnel for")


def profile_teams():
    return Team.query.filter_by(orgid=g.profile.userid).order_by(Team.title)


class EditProfileForm(forms.Form):
    """
    Edit a profile.
    """
    description = forms.MarkdownField(u"Welcome message",
        validators=[forms.validators.DataRequired(_(u"Please write a message for the landing page"))],
        description=_(u"This welcome message will be shown on the landing page."))
    admin_team = QuerySelectField(u"Admin Team",
        validators=[forms.validators.DataRequired(_(u"Please select a team"))],
        query_factory=profile_teams, get_label='title', allow_blank=False,
        description=_(u"The team of users with administrative rights to this Talkfunnel (owners always have admin access)"))
