"""Forms for organizations and teams."""

from __future__ import annotations

from collections.abc import Iterable

from flask import url_for
from markupsafe import Markup

from baseframe import _, __, forms

from ..models import Account, AccountNameProblem, Team, User

__all__ = ['OrganizationForm', 'TeamForm']


@Account.forms('org')
class OrganizationForm(forms.Form):
    """Form for an organization's name and title."""

    __expects__: Iterable[str] = ('edit_user',)
    edit_user: User
    edit_obj: Account | None

    title = forms.StringField(
        __("Organization name"),
        description=__(
            "Your organization’s given name, without legal suffixes such as Pvt Ltd"
        ),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=Account.__title_length__),
        ],
        filters=[forms.filters.strip()],
        render_kw={'autocomplete': 'organization'},
    )
    name = forms.AnnotatedTextField(
        __("Username"),
        description=__(
            "A unique word for your organization’s account page. Alphabets, numbers and"
            " underscores are okay. Pick something permanent: changing it will break"
            " links"
        ),
        validators=[
            forms.validators.DataRequired(),
            forms.validators.Length(max=Account.__name_length__),
        ],
        filters=[forms.filters.strip()],
        prefix="https://hasgeek.com/",
        render_kw={'autocorrect': 'off', 'autocapitalize': 'off'},
    )

    def validate_name(self, field: forms.Field) -> None:
        """Validate name is valid and available for this account."""
        if self.edit_obj:
            reason = self.edit_obj.validate_new_name(field.data)
        else:
            reason = Account.validate_name_candidate(field.data)
        if not reason:
            return  # name is available
        match reason:
            case AccountNameProblem.INVALID:
                raise forms.validators.ValidationError(
                    _("Names can only have alphabets, numbers and underscores")
                )
            case AccountNameProblem.RESERVED:
                raise forms.validators.ValidationError(_("This name is reserved"))
            case AccountNameProblem.USER:
                if self.edit_user.name_is(field.data):
                    raise forms.validators.ValidationError(
                        Markup(  # noqa: S704
                            _(
                                'This is <em>your</em> current username.'
                                ' You must change it first from <a href="'
                                '{url}">your account</a> before you can assign it'
                                ' to an organization'
                            )
                        ).format(url=url_for('account'))
                    )
                raise forms.validators.ValidationError(
                    _("This name has been taken by another user")
                )
            case AccountNameProblem.ORG:
                raise forms.validators.ValidationError(
                    _("This name has been taken by another organization")
                )
            case _:
                raise forms.validators.ValidationError(
                    _("This name has been taken by another account")
                )


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
            "Team members will be listed on the organization’s account page"
        ),
        default=True,
    )
