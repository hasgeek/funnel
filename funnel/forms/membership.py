# -*- coding: utf-8 -*-

from baseframe import _, __
import baseframe.forms as forms


class ProjectMembershipForm(forms.Form):
    # add a member to a project
    user = forms.UserSelectField(
        __("User"),
        validators=[forms.validators.DataRequired(_(u"Please select a user"))],
        description=__("The user who you want to add to this project"),
    )
    is_editor = forms.BooleanField(__("Editor"), default=False)
    is_concierge = forms.BooleanField(__("Concierge"), default=False)
    is_usher = forms.BooleanField(__("Usher"), default=False)
