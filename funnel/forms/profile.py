# -*- coding: utf-8 -*-

import wtforms
from baseframe.forms import Form


class NewProfileForm(Form):
    """
    Create a new profile.
    """
    profile = wtforms.RadioField(u"Organization", validators=[wtforms.validators.Required("Select an organization")],
        description=u"Select the organization you’d like to create a talk funnel for")
