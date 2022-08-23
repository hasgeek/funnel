"""Forms for organizations and teams."""

from __future__ import annotations

from typing import Iterable, Optional

from flask import Markup, url_for

from baseframe import _, __, forms

from ..models import Organization, Profile, Team, User

__all__ = ['OrganizationForm', 'TeamForm']


@Organization.forms('main')
class OrganizationForm(forms.Form):
    """Form for an organization's name and title."""

    __expects__: Iterable[str] = ('user',)
    user: User
    edit_obj: Optional[Organization]

    title = forms.StringField(
        __("Organization name"),
        description=__(
            "Your organization’s given name, without legal suffixes such as Pvt Ltd"
        ),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=Organization.__title_length__),
        ],
        filters=[forms.filters.strip()],
        render_kw={'autocomplete': 'organization'},
    )
    name = forms.AnnotatedTextField(
        __("Username"),
        description=__(
            "A short name for your organization’s profile page."
            " Single word containing letters, numbers and dashes only."
            " Pick something permanent: changing it will break existing links from"
            " around the web"
        ),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=Profile.__name_length__),
        ],
        filters=[forms.filters.strip()],
        prefix="https://hasgeek.com/",
        render_kw={'autocorrect': 'off', 'autocapitalize': 'off'},
    )

    def validate_name(self, field) -> None:
        """Validate name is valid and available for this organization."""
        reason = Profile.validate_name_candidate(field.data)
        if not reason:
            return  # name is available
        if reason == 'invalid':
            raise forms.validators.ValidationError(
                _(
                    "Names can only have letters, numbers and dashes (except at the"
                    " ends)"
                )
            )
        if reason == 'reserved':
            raise forms.validators.ValidationError(_("This name is reserved"))
        if self.edit_obj and field.data.lower() == self.edit_obj.name.lower():
            # Name is not reserved or invalid under current rules. It's also not changed
            # from existing name, or has only changed case. This is a validation pass.
            return
        if reason == 'user':
            if self.user.username and field.data.lower() == self.user.username.lower():
                raise forms.validators.ValidationError(
                    Markup(
                        _(
                            "This is <em>your</em> current username."
                            ' You must change it first from <a href="{account}">your'
                            " account</a> before you can assign it to an organization"
                        ).format(account=url_for('account'))
                    )
                )
            raise forms.validators.ValidationError(
                _("This name has been taken by another user")
            )
        if reason == 'org':
            raise forms.validators.ValidationError(
                _("This name has been taken by another organization")
            )
        # We're not supposed to get an unknown reason. Flag error to developers.
        raise ValueError(f"Unknown profile name validation failure reason: {reason}")


@Team.forms('main')
class TeamForm(forms.Form):
    """Form for a team in an organization."""

    title = forms.StringField(
        __("Team name"),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=Team.__title_length__),
        ],
        filters=[forms.filters.strip()],
    )
    users = forms.UserSelectMultiField(
        __("Users"),
        validators=[forms.validators.DataRequired()],
        description=__("Lookup a user by their username or email address"),
    )
    is_public = forms.BooleanField(
        __("Make this team public"),
        description=__(
            "Team members will be listed on the organization’s profile page"
        ),
        default=True,
    )
