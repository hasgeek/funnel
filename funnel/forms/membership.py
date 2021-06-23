from __future__ import annotations

from baseframe import _, __
from coaster.utils import getbool
import baseframe.forms as forms

from ..models import OrganizationMembership, ProjectCrewMembership

__all__ = [
    'OrganizationMembershipForm',
    'ProjectCrewMembershipForm',
    'ProjectCrewMembershipInviteForm',
]


@OrganizationMembership.forms('main')
class OrganizationMembershipForm(forms.Form):
    # add a member to a project
    user = forms.UserSelectField(
        __("User"),
        validators=[forms.validators.DataRequired(_("Please select a user"))],
        description=__("Find a user by their name or email address"),
    )
    is_owner = forms.RadioField(
        __("Access level"),
        coerce=getbool,
        default=False,
        choices=[
            (
                False,
                __("Admin (can manage projects, but can’t add or remove other admins)"),
            ),
            (True, __("Owner (can also manage other owners and admins)")),
        ],
    )


@ProjectCrewMembership.forms('main')
class ProjectCrewMembershipForm(forms.Form):
    # add a member to a project
    user = forms.UserSelectField(
        __("User"),
        validators=[forms.validators.DataRequired(_("Please select a user"))],
        description=__("Find a user by their name or email address"),
    )
    is_editor = forms.BooleanField(
        __("Editor"),
        default=False,
        description=__(
            "Can edit project details, proposal guidelines, schedule, labels and venues"
        ),
    )
    is_promoter = forms.BooleanField(
        __("Promoter"),
        default=False,
        description=__("Can manage participants and see contact info"),
    )
    is_usher = forms.BooleanField(
        __("Usher"),
        default=False,
        description=__(
            "Can check-in a participant using their badge at a physical event"
        ),
    )

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators)
        if not any([self.is_editor.data, self.is_promoter.data, self.is_usher.data]):
            self.is_usher.errors.append("Please select one or more roles")
            is_valid = False
        return is_valid


@ProjectCrewMembership.forms('invite')
class ProjectCrewMembershipInviteForm(forms.Form):
    action = forms.SelectField(
        __("Choice"),
        choices=[('accept', __("Accept")), ('decline', __("Decline"))],
        validators=[forms.validators.DataRequired(_("Please make a choice"))],
    )
