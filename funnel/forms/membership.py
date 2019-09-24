# -*- coding: utf-8 -*-

from baseframe import _, __
import baseframe.forms as forms


class ProjectCrewMembershipForm(forms.Form):
    # add a member to a project
    user = forms.UserSelectField(
        __("User"),
        validators=[forms.validators.DataRequired(_(u"Please select a user"))],
        description=__("Find a user by their name or email address"),
    )
    is_editor = forms.BooleanField(__("Editor"), default=False)
    is_concierge = forms.BooleanField(__("Concierge"), default=False)
    is_usher = forms.BooleanField(__("Usher"), default=False)

    def validate(self, extra_validators=None):
        is_valid = super(ProjectCrewMembershipForm, self).validate(extra_validators)
        if not any([self.is_editor.data, self.is_concierge.data, self.is_usher.data]):
            self.is_usher.errors.append("Please select one or more roles")
            is_valid = False
        return is_valid


class ProjectCrewMembershipInviteForm(forms.Form):
    action = forms.SelectField(
        __("Choice"),
        choices=[('accept', __("Accept")), ('decline', __("Decline"))],
        validators=[forms.validators.DataRequired(_(u"Please make a choice"))],
    )
