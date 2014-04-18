# -*- coding: utf-8 -*-

import wtforms
from baseframe.forms import Form, MarkdownField


class NewProfileForm(Form):
    """
    Create a new profile.
    """
    profile = wtforms.RadioField(u"Organization", validators=[wtforms.validators.Required("Select an organization")],
        description=u"Select the organization you’d like to create a Talkfunnel for")


class EditProfileForm(Form):
    """
    Edit a profile.
    """
    description = MarkdownField(u"Welcome message",
        description=u"This welcome message will be shown on the landing page.")
