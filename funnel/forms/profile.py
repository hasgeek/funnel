# -*- coding: utf-8 -*-

from flask import g
import wtforms
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from baseframe import _
from baseframe.forms import Form, MarkdownField
from ..models import Team


class NewProfileForm(Form):
    """
    Create a new profile.
    """
    profile = wtforms.RadioField(u"Organization", validators=[wtforms.validators.Required("Select an organization")],
        description=u"Select the organization you’d like to create a Talkfunnel for")


def profile_teams():
    return Team.query.filter_by(orgid=g.profile.userid).order_by(Team.title)


class EditProfileForm(Form):
    """
    Edit a profile.
    """
    description = MarkdownField(u"Welcome message",
        validators=[wtforms.validators.Required(_(u"Please write a message for the landing page"))],
        description=_(u"This welcome message will be shown on the landing page."))
    admin_team = QuerySelectField(u"Admin Team",
        validators=[wtforms.validators.Required(_(u"Please select a team"))],
        query_factory=profile_teams, get_label='title', allow_blank=False,
        description=_(u"The team of users with administrative rights to this Talkfunnel (owners always have admin access)"))
