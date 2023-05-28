"""Forms for organization admin and project crew memberships."""

from __future__ import annotations

from baseframe import _, __, forms
from coaster.utils import getbool

from ..models import OrganizationMembership, ProjectCrewMembership
from .helpers import nullable_strip_filters

__all__ = [
    'OrganizationMembershipForm',
    'ProjectCrewMembershipForm',
    'ProjectCrewMembershipInviteForm',
]


@OrganizationMembership.forms('main')
class OrganizationMembershipForm(forms.Form):
    """Form to add a member to an organization (admin or owner)."""

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
    """Form to add a project crew member."""

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
    label = forms.StringField(
        __("Role"),
        description=__("Optional – Name this person’s role"),
        filters=nullable_strip_filters,
    )

    def validate(self, *args, **kwargs) -> bool:
        """Validate form."""
        is_valid = super().validate(*args, **kwargs)
        if not any([self.is_editor.data, self.is_promoter.data, self.is_usher.data]):
            self.is_usher.errors.append(_("Select one or more roles"))
            is_valid = False
        return is_valid


@ProjectCrewMembership.forms('invite')
class ProjectCrewMembershipInviteForm(forms.Form):
    """Form to invite a user to be a project crew member."""

    action = forms.SelectField(
        __("Choice"),
        choices=[('accept', __("Accept")), ('decline', __("Decline"))],
        validators=[forms.validators.DataRequired(_("Please make a choice"))],
    )
